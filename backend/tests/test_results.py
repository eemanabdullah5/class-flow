from datetime import datetime, timedelta, timezone

import pytest

from app.models import Assignment, Grade, Submission
from tests.conftest import auth_header

NOW = datetime.now(timezone.utc)


def add_assignment(session, classroom, title, category, max_points, days_from_now):
    """Added straight to the database, because the API refuses due dates in the past."""
    assignment = Assignment(
        course_id=classroom["course"].id,
        title=title,
        category=category,
        max_points=max_points,
        due_at=NOW + timedelta(days=days_from_now),
    )
    session.add(assignment)
    session.commit()
    return assignment


def hand_in(session, assignment, student, status="submitted", hours_after_due=-1):
    """A submission; by default marked as done an hour before the due date."""
    session.add(
        Submission(
            assignment_id=assignment.id,
            student_id=student.id,
            status=status,
            original_filename="work.pdf",
            stored_filename=f"{assignment.id}-{student.id}.pdf",
            content_type="application/pdf",
            file_size=100,
            submitted_at=assignment.due_at + timedelta(hours=hours_after_due) if status == "submitted" else None,
        )
    )
    session.commit()


def give_grade(session, classroom, assignment, student, score):
    session.add(
        Grade(assignment_id=assignment.id, student_id=student.id, score=score, graded_by=classroom["teacher"].id)
    )
    session.commit()


@pytest.fixture
def gradebook(session, classroom):
    """One of each category. "student" has grades; "classmate" has missing, late and waiting work.
    (The classroom fixture's own "Assignment 1", due next week, is there too and counts for nothing yet.)

    Quiz 1 (10 pts, 3 days ago)     student 8        classmate: only a draft -> missing (0)
    Homework 1 (20 pts, 2 days ago) student 15 (on time)   classmate: handed in late, not graded yet
    Midterm (50 pts, yesterday)     student 35       classmate: no mark entered yet
    Project (100 pts, next week)    nobody yet
    """
    student, classmate = classroom["student"], classroom["classmate"]
    quiz = add_assignment(session, classroom, "Quiz 1", "quiz", 10, -3)
    homework = add_assignment(session, classroom, "Homework 1", "assignment", 20, -2)
    midterm = add_assignment(session, classroom, "Midterm", "midterm", 50, -1)
    project = add_assignment(session, classroom, "Project", "project", 100, 7)

    give_grade(session, classroom, quiz, student, 8)
    hand_in(session, quiz, classmate, status="draft")
    hand_in(session, homework, student)
    give_grade(session, classroom, homework, student, 15)
    hand_in(session, homework, classmate, hours_after_due=5)
    give_grade(session, classroom, midterm, student, 35)
    return {"quiz": quiz, "homework": homework, "midterm": midterm, "project": project}


def get(client, classroom, path, user_key):
    return client.get(f"/api/courses/{classroom['course'].id}/{path}", headers=auth_header(classroom[user_key]))


def by_category(result):
    return {c["category"]: c for c in result["categories"]}


# ---------- a student's own result ----------


def test_student_result_uses_the_fixed_weights(client, classroom, gradebook):
    response = get(client, classroom, "my-result", "student")

    assert response.status_code == 200
    result = response.json()
    # quiz 8/10 = 80%, assignment 15/20 = 75%, midterm 35/50 = 70%, project not counted yet:
    # (10 * 80 + 10 * 75 + 30 * 70) / (10 + 10 + 30) = 73.0
    assert result["percentage"] == 73.0
    assert result["letter"] == "B"
    assert result["passed"] is True
    categories = by_category(result)
    assert categories["quiz"] == {"category": "quiz", "weight": 10, "earned": 8, "possible": 10, "percentage": 80.0}
    assert categories["midterm"]["percentage"] == 70.0
    assert categories["project"] == {
        "category": "project",
        "weight": 50,
        "earned": None,
        "possible": None,
        "percentage": None,
    }


def test_missing_counts_as_zero_and_waiting_work_doesnt_count(client, classroom, gradebook):
    result = get(client, classroom, "my-result", "classmate").json()

    categories = by_category(result)
    assert categories["quiz"]["earned"] == 0  # a draft after the deadline is missing
    assert categories["assignment"]["possible"] is None  # handed in, waiting for a grade
    assert categories["midterm"]["possible"] is None  # no mark entered yet
    assert (result["percentage"], result["letter"], result["passed"]) == (0.0, "F", False)


def test_nothing_counts_before_any_due_date(client, session, classroom):
    add_assignment(session, classroom, "Project", "project", 100, 7)

    result = get(client, classroom, "my-result", "student").json()

    assert (result["percentage"], result["letter"], result["passed"]) == (None, None, None)


def test_result_rounds_then_grades_from_the_rounded_number(client, session, classroom):
    quiz = add_assignment(session, classroom, "Quiz", "quiz", 3, -1)
    give_grade(session, classroom, quiz, classroom["student"], 1.5)  # exactly 50%

    result = get(client, classroom, "my-result", "student").json()

    assert (result["percentage"], result["letter"], result["passed"]) == (50.0, "D", True)


def test_teacher_cannot_ask_for_my_result(client, classroom, gradebook):
    assert get(client, classroom, "my-result", "teacher").status_code == 403


def test_outsider_cannot_ask_for_my_result(client, classroom, gradebook):
    assert get(client, classroom, "my-result", "outsider").status_code == 404


# ---------- the teacher's class results ----------


def test_teacher_sees_every_student_and_class_stats(client, classroom, gradebook):
    response = get(client, classroom, "results", "teacher")

    assert response.status_code == 200
    body = response.json()
    assert [row["result"]["percentage"] for row in body["students"]] == [73.0, 0.0]
    assert [row["student"]["id"] for row in body["students"]] == [classroom["student"].id, classroom["classmate"].id]
    # percentages 73 and 0: mean 36.5, variance ((36.5)^2 + (36.5)^2) / 2 = 1332.25, 1 of 2 passed
    assert body["stats"] == {
        "count": 2,
        "mean": 36.5,
        "minimum": 0.0,
        "maximum": 73.0,
        "variance": 1332.25,
        "pass_proportion": 0.5,
    }
    assert body["pass_percent"] == 50
    assert body["letter_scale"][0] == {"lowest": 80, "letter": "A"}


def test_students_without_a_result_are_listed_but_not_in_the_stats(client, session, classroom):
    quiz = add_assignment(session, classroom, "Quiz", "quiz", 10, 7)  # not due yet
    give_grade(session, classroom, quiz, classroom["student"], 9)

    body = get(client, classroom, "results", "teacher").json()

    assert len(body["students"]) == 2
    assert body["students"][1]["result"]["percentage"] is None
    assert body["stats"]["count"] == 1
    assert body["stats"]["variance"] == 0


def test_class_with_no_results_has_empty_stats(client, classroom):
    stats = get(client, classroom, "results", "teacher").json()["stats"]

    assert stats["count"] == 0
    assert stats["mean"] is None


def test_student_cannot_see_class_results(client, classroom, gradebook):
    assert get(client, classroom, "results", "student").status_code == 403


def test_other_teacher_cannot_see_class_results(client, classroom, gradebook):
    assert get(client, classroom, "results", "other_teacher").status_code == 404


@pytest.mark.parametrize("path", ["my-result", "results"])
def test_results_need_a_login(client, classroom, path):
    assert client.get(f"/api/courses/{classroom['course'].id}/{path}").status_code == 401


# ---------- categories and in-class work ----------


def create_assignment(client, classroom, **changes):
    body = {"title": "Quiz 1", "max_points": 10, "due_at": (NOW + timedelta(days=7)).isoformat(), **changes}
    return client.post(
        f"/api/courses/{classroom['course'].id}/assignments", json=body, headers=auth_header(classroom["teacher"])
    )


@pytest.mark.parametrize("category", ["quiz", "assignment", "midterm", "project"])
def test_teacher_creates_each_category(client, classroom, category):
    response = create_assignment(client, classroom, category=category)

    assert response.status_code == 201
    assert response.json()["category"] == category


def test_category_defaults_to_assignment(client, classroom):
    assert create_assignment(client, classroom).json()["category"] == "assignment"


def test_midterm_has_nothing_to_upload_or_turn_in(client, classroom):
    midterm_id = create_assignment(client, classroom, category="midterm").json()["id"]
    student = auth_header(classroom["student"])

    upload = client.put(
        f"/api/assignments/{midterm_id}/submission",
        files={"file": ("exam.pdf", b"%PDF-1.4 answers", "application/pdf")},
        headers=student,
    )
    turn_in = client.post(f"/api/assignments/{midterm_id}/submission/turn-in", headers=student)

    assert upload.status_code == 409
    assert "taken in class" in upload.json()["detail"]
    assert turn_in.status_code == 409


def test_midterm_can_be_graded_before_its_date(client, classroom):
    midterm_id = create_assignment(client, classroom, category="midterm", max_points=50).json()["id"]

    response = client.put(
        f"/api/assignments/{midterm_id}/grades/{classroom['student'].id}",
        json={"score": 42},
        headers=auth_header(classroom["teacher"]),
    )

    assert response.status_code == 200


def test_category_can_be_changed(client, classroom):
    assignment_id = create_assignment(client, classroom).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={"category": "project"}, headers=auth_header(classroom["teacher"])
    )

    assert response.json()["category"] == "project"


def test_work_with_uploads_cant_become_a_midterm(client, classroom):
    assignment_id = create_assignment(client, classroom).json()["id"]
    client.put(
        f"/api/assignments/{assignment_id}/submission",
        files={"file": ("work.pdf", b"%PDF-1.4 my work", "application/pdf")},
        headers=auth_header(classroom["student"]),
    )

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={"category": "midterm"}, headers=auth_header(classroom["teacher"])
    )

    assert response.status_code == 409
    assert "already uploaded" in response.json()["detail"]


@pytest.mark.parametrize("category", ["exam", None])
def test_bad_category_is_rejected(client, classroom, category):
    assignment_id = create_assignment(client, classroom).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={"category": category}, headers=auth_header(classroom["teacher"])
    )

    assert response.status_code == 422
