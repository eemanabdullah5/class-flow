import pytest

from tests.conftest import auth_header
from tests.test_results import add_assignment, gradebook  # noqa: F401  (gradebook is a fixture)


def report(client, classroom, name, user_key="teacher"):
    return client.get(
        f"/api/courses/{classroom['course'].id}/reports/{name}", headers=auth_header(classroom[user_key])
    )


# ---------- 1. assignment summary ----------


def test_assignment_summary_counts_each_assignment(client, classroom, gradebook):  # noqa: F811
    response = report(client, classroom, "assignments")

    assert response.status_code == 200
    rows = {row["title"]: row for row in response.json()}
    # Soonest due first; "Assignment 1" (from the classroom fixture) and Project are both due next week.
    assert [row["title"] for row in response.json()][:3] == ["Quiz 1", "Homework 1", "Midterm"]
    assert set(rows) == {"Quiz 1", "Homework 1", "Midterm", "Project", "Assignment 1"}

    quiz = rows["Quiz 1"]
    assert (quiz["enrolled"], quiz["turned_in"], quiz["late"], quiz["missing"], quiz["graded"]) == (2, 0, 0, 1, 1)
    assert (quiz["average_score"], quiz["lowest_score"], quiz["highest_score"]) == (8, 8, 8)

    homework = rows["Homework 1"]
    assert (homework["turned_in"], homework["late"], homework["missing"], homework["graded"]) == (2, 1, 0, 1)

    assert rows["Midterm"]["missing"] is None  # in class: nothing to hand in
    assert rows["Midterm"]["average_score"] == 35

    project = rows["Project"]
    assert (project["missing"], project["graded"], project["average_score"]) == (0, 0, None)  # not due yet


def test_assignment_summary_returns_times_in_utc(client, classroom, gradebook):  # noqa: F811
    due = report(client, classroom, "assignments").json()[0]["due_at"]

    assert due.endswith("Z") or due.endswith("+00:00")
    assert due.startswith(gradebook["quiz"].due_at.isoformat()[:19])


def test_average_is_over_graded_students(client, session, classroom):
    quiz = add_assignment(session, classroom, "Quiz", "quiz", 10, -1)
    for student_key, score in [("student", 4), ("classmate", 9)]:
        client.put(
            f"/api/assignments/{quiz.id}/grades/{classroom[student_key].id}",
            json={"score": score},
            headers=auth_header(classroom["teacher"]),
        )

    row = next(r for r in report(client, classroom, "assignments").json() if r["title"] == "Quiz")

    assert (row["average_score"], row["lowest_score"], row["highest_score"]) == (6.5, 4, 9)


# ---------- 2. student progress ----------


def test_student_progress_per_student(client, classroom, gradebook):  # noqa: F811
    rows = report(client, classroom, "students").json()

    assert [row["id"] for row in rows] == [classroom["student"].id, classroom["classmate"].id]
    student, classmate = rows
    assert (student["turned_in"], student["late"], student["graded"]) == (1, 0, 3)
    assert (student["points_earned"], student["points_possible"]) == (58, 80)  # 8 + 15 + 35 of 10 + 20 + 50
    assert (classmate["turned_in"], classmate["late"], classmate["graded"]) == (1, 1, 0)
    assert (classmate["points_earned"], classmate["points_possible"]) == (0, 0)


def test_student_progress_only_counts_this_course(client, session, classroom, gradebook):  # noqa: F811
    from app.models import Assignment, Course, Enrollment, Grade

    other = Course(title="Databases", teacher_id=classroom["teacher"].id, join_code="DB5678")
    session.add(other)
    session.commit()
    assignment = Assignment(course_id=other.id, title="SQL", max_points=10, due_at=gradebook["quiz"].due_at)
    session.add_all([assignment, Enrollment(course_id=other.id, student_id=classroom["student"].id)])
    session.commit()
    session.add(Grade(assignment_id=assignment.id, student_id=classroom["student"].id, score=10, graded_by=classroom["teacher"].id))
    session.commit()

    student = report(client, classroom, "students").json()[0]

    assert (student["graded"], student["points_earned"]) == (3, 58)


# ---------- 3. missing and late work ----------


def test_missing_and_late_lists_each_problem(client, classroom, gradebook):  # noqa: F811
    rows = report(client, classroom, "missing-late").json()

    assert [(row["assignment_title"], row["student_id"], row["problem"]) for row in rows] == [
        ("Quiz 1", classroom["classmate"].id, "missing"),  # only a draft
        ("Homework 1", classroom["classmate"].id, "late"),  # handed in 5 hours late
    ]
    assert rows[0]["submitted_at"] is None
    assert rows[1]["submitted_at"] is not None


def test_graded_missing_work_is_no_longer_listed(client, classroom, gradebook):  # noqa: F811
    client.put(
        f"/api/assignments/{gradebook['quiz'].id}/grades/{classroom['classmate'].id}",
        json={"score": 0},
        headers=auth_header(classroom["teacher"]),
    )

    rows = report(client, classroom, "missing-late").json()

    assert [row["problem"] for row in rows] == ["late"]


def test_nothing_is_missing_before_the_due_date(client, session, classroom):
    add_assignment(session, classroom, "Project", "project", 100, 7)

    assert report(client, classroom, "missing-late").json() == []


# ---------- permissions ----------


@pytest.mark.parametrize("name", ["assignments", "students", "missing-late"])
def test_student_cannot_see_reports(client, classroom, name):
    assert report(client, classroom, name, user_key="student").status_code == 403


@pytest.mark.parametrize("name", ["assignments", "students", "missing-late"])
def test_other_teacher_cannot_see_reports(client, classroom, name):
    assert report(client, classroom, name, user_key="other_teacher").status_code == 404


@pytest.mark.parametrize("name", ["assignments", "students", "missing-late"])
def test_reports_need_a_login(client, classroom, name):
    assert client.get(f"/api/courses/{classroom['course'].id}/reports/{name}").status_code == 401
