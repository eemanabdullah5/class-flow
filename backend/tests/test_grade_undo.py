from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import Assignment, Course, Enrollment, Grade, GradeChange
from tests.conftest import auth_header
from tests.test_grades import grade, my_grade, turn_in, upload


def preview(client, user):
    return client.get("/api/grades/undo", headers=auth_header(user))


def undo(client, user):
    return client.post("/api/grades/undo", headers=auth_header(user))


def submitted_and_graded(client, classroom, *scores):
    """The student hands in work, then the teacher gives each score in turn."""
    upload(client, classroom)
    turn_in(client, classroom)
    for score in scores:
        grade(client, classroom, score=score, feedback=f"Feedback for {score:g}")


def change_count(session):
    return session.scalar(select(func.count()).select_from(GradeChange))


# ---------- undo puts the old grade back ----------


def test_undo_restores_the_previous_score_feedback_and_time(client, session, classroom):
    submitted_and_graded(client, classroom, 12)
    first = session.scalars(select(Grade)).one()
    first_graded_at = first.graded_at
    grade(client, classroom, score=15, feedback="Re-marked")

    response = undo(client, classroom["teacher"])

    assert response.status_code == 200
    restored = my_grade(client, classroom).json()
    assert (restored["score"], restored["feedback"]) == (12, "Feedback for 12")
    session.expire_all()
    assert session.scalars(select(Grade)).one().graded_at == first_graded_at


def test_undo_goes_back_newest_first(client, classroom):
    submitted_and_graded(client, classroom, 10, 14, 17)
    teacher = classroom["teacher"]

    undo(client, teacher)
    assert my_grade(client, classroom).json()["score"] == 14
    undo(client, teacher)
    assert my_grade(client, classroom).json()["score"] == 10
    undo(client, teacher)
    assert my_grade(client, classroom).json() is None


def test_undoing_a_first_grade_deletes_it_and_unlocks_the_work(client, classroom):
    submitted_and_graded(client, classroom, 18)
    unsubmit_url = f"/api/assignments/{classroom['assignment'].id}/submission/unsubmit"
    student_header = auth_header(classroom["student"])
    assert client.post(unsubmit_url, headers=student_header).status_code == 409  # locked

    undo(client, classroom["teacher"])

    assert my_grade(client, classroom).json() is None
    assert client.post(unsubmit_url, headers=student_header).status_code == 200


def test_undo_is_not_recorded_as_a_new_change(client, session, classroom):
    submitted_and_graded(client, classroom, 10, 14)

    undo(client, classroom["teacher"])

    assert change_count(session) == 2  # still only the two real changes, so no redo


# ---------- preview and empty stack ----------


def test_preview_says_what_undo_will_do(client, classroom):
    submitted_and_graded(client, classroom, 18)
    teacher = classroom["teacher"]

    response = preview(client, teacher)

    assert response.status_code == 200
    assert response.json() == {
        "assignment_id": classroom["assignment"].id,
        "assignment_title": "Assignment 1",
        "student_id": classroom["student"].id,
        "student_name": classroom["student"].full_name,
        "from_score": 18,
        "to_score": None,  # 18 -> no grade
    }
    assert undo(client, teacher).json() == response.json()


def test_preview_changes_nothing(client, classroom):
    submitted_and_graded(client, classroom, 10, 14)

    preview(client, classroom["teacher"])
    preview(client, classroom["teacher"])

    assert my_grade(client, classroom).json()["score"] == 14
    assert preview(client, classroom["teacher"]).json()["to_score"] == 10


def test_preview_moves_down_the_stack_after_each_undo(client, classroom):
    submitted_and_graded(client, classroom, 10, 14)
    teacher = classroom["teacher"]

    undo(client, teacher)

    assert preview(client, teacher).json()["from_score"] == 10
    assert preview(client, teacher).json()["to_score"] is None


def test_nothing_to_undo_when_nothing_was_graded(client, classroom):
    teacher = classroom["teacher"]

    assert preview(client, teacher).status_code == 200
    assert preview(client, teacher).json() is None
    response = undo(client, teacher)
    assert response.status_code == 409
    assert response.json()["detail"] == "Nothing to undo."


def test_nothing_to_undo_after_everything_is_undone(client, classroom):
    submitted_and_graded(client, classroom, 10, 14)
    teacher = classroom["teacher"]
    undo(client, teacher)
    undo(client, teacher)

    assert preview(client, teacher).json() is None
    assert undo(client, teacher).status_code == 409


# ---------- each teacher has their own stack ----------


def give_other_teacher_a_graded_student(session, client, classroom):
    """Another course, taught by other_teacher, with the outsider graded 9/10."""
    course = Course(title="Databases", teacher_id=classroom["other_teacher"].id, join_code="DB5678")
    session.add(course)
    session.commit()
    assignment = Assignment(
        course_id=course.id,
        title="ER diagram",
        max_points=10,
        due_at=datetime.now(timezone.utc) - timedelta(hours=1),  # past, so missing work can be graded
    )
    session.add_all([assignment, Enrollment(course_id=course.id, student_id=classroom["outsider"].id)])
    session.commit()
    client.put(
        f"/api/assignments/{assignment.id}/grades/{classroom['outsider'].id}",
        json={"score": 9},
        headers=auth_header(classroom["other_teacher"]),
    )
    return assignment


def test_teacher_only_undoes_their_own_changes(client, session, classroom):
    submitted_and_graded(client, classroom, 18)
    give_other_teacher_a_graded_student(session, client, classroom)  # the newest change overall

    response = undo(client, classroom["teacher"])

    assert response.json()["assignment_title"] == "Assignment 1"
    assert my_grade(client, classroom).json() is None
    other_grade = session.scalars(select(Grade).where(Grade.student_id == classroom["outsider"].id)).one()
    assert other_grade.score == 9  # the other teacher's grade is untouched


def test_other_teachers_preview_shows_only_their_own_change(client, session, classroom):
    submitted_and_graded(client, classroom, 18)

    assert preview(client, classroom["other_teacher"]).json() is None
    assert undo(client, classroom["other_teacher"]).status_code == 409
    assert my_grade(client, classroom).json()["score"] == 18

    give_other_teacher_a_graded_student(session, client, classroom)
    assert preview(client, classroom["other_teacher"]).json()["assignment_title"] == "ER diagram"


# ---------- permissions ----------


@pytest.mark.parametrize("send", [preview, undo])
def test_student_cannot_undo_or_preview(client, classroom, send):
    submitted_and_graded(client, classroom, 18)

    assert send(client, classroom["student"]).status_code == 403
    assert my_grade(client, classroom).json()["score"] == 18


@pytest.mark.parametrize("method", ["get", "post"])
def test_undo_needs_a_login(client, method):
    assert getattr(client, method)("/api/grades/undo").status_code == 401
