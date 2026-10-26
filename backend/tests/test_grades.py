from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Grade, GradeChange
from tests.conftest import auth_header

PDF = b"%PDF-1.4\npretend homework\n"


def upload(client, classroom, user_key="student"):
    return client.put(
        f"/api/assignments/{classroom['assignment'].id}/submission",
        files={"file": ("homework.pdf", PDF, "application/pdf")},
        headers=auth_header(classroom[user_key]),
    )


def turn_in(client, classroom, user_key="student"):
    return client.post(
        f"/api/assignments/{classroom['assignment'].id}/submission/turn-in",
        headers=auth_header(classroom[user_key]),
    )


def grade(client, classroom, score=18, feedback="Good work", student_key="student", user_key="teacher"):
    student_id = classroom[student_key].id
    return client.put(
        f"/api/assignments/{classroom['assignment'].id}/grades/{student_id}",
        json={"score": score, "feedback": feedback},
        headers=auth_header(classroom[user_key]),
    )


def work_list(client, classroom, user_key="teacher"):
    return client.get(
        f"/api/assignments/{classroom['assignment'].id}/submissions",
        headers=auth_header(classroom[user_key]),
    )


def my_grade(client, classroom, user_key="student"):
    return client.get(
        f"/api/assignments/{classroom['assignment'].id}/my-grade",
        headers=auth_header(classroom[user_key]),
    )


def recorded_changes(session):
    """Every grade change written down for undo, oldest first."""
    return session.scalars(select(GradeChange).order_by(GradeChange.id)).all()


def move_due_date_to_the_past(session, classroom):
    classroom["assignment"].due_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.commit()


# ---------- the teacher's list ----------


def test_list_shows_every_enrolled_student_including_missing(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)

    response = work_list(client, classroom)

    assert response.status_code == 200
    rows = {row["student"]["id"]: row for row in response.json()}
    assert len(rows) == 2  # the outsider is not listed
    assert rows[classroom["student"].id]["status"] == "submitted"
    assert rows[classroom["student"].id]["submission"]["original_filename"] == "homework.pdf"
    assert rows[classroom["classmate"].id]["status"] == "missing"
    assert rows[classroom["classmate"].id]["submission"] is None


def test_list_includes_grades_once_given(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=17)

    rows = {row["student"]["id"]: row for row in work_list(client, classroom).json()}

    assert rows[classroom["student"].id]["grade"]["score"] == 17
    assert rows[classroom["classmate"].id]["grade"] is None


def test_student_cannot_see_the_teachers_list(client, classroom):
    assert work_list(client, classroom, user_key="student").status_code == 403


def test_other_teacher_cannot_see_the_list(client, classroom):
    assert work_list(client, classroom, user_key="other_teacher").status_code == 404


# ---------- grading ----------


def test_teacher_grades_submitted_work(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)

    response = grade(client, classroom, score=18, feedback="Nice job")

    assert response.status_code == 200
    assert response.json()["score"] == 18
    assert response.json()["feedback"] == "Nice job"


def test_changing_a_grade_updates_it(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=12)

    response = grade(client, classroom, score=15, feedback="Re-marked")

    assert response.json()["score"] == 15
    assert my_grade(client, classroom).json()["score"] == 15


@pytest.mark.parametrize("score", [-1, 20.5, 100])
def test_score_must_be_between_zero_and_max_points(client, classroom, score):
    upload(client, classroom)
    turn_in(client, classroom)

    assert grade(client, classroom, score=score).status_code == 422


def test_full_marks_are_allowed(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)

    assert grade(client, classroom, score=20).status_code == 200


def test_missing_work_can_be_given_zero(client, classroom):
    response = grade(client, classroom, score=0, feedback="Not submitted", student_key="classmate")

    assert response.status_code == 200
    assert response.json()["score"] == 0


def test_draft_cannot_be_graded_before_the_deadline(client, classroom):
    upload(client, classroom)  # uploaded but not marked as done

    response = grade(client, classroom)

    assert response.status_code == 409
    assert "still a draft" in response.json()["detail"]


def test_draft_can_be_graded_after_the_deadline(client, session, classroom):
    upload(client, classroom)
    move_due_date_to_the_past(session, classroom)

    assert grade(client, classroom, score=0).status_code == 200


def test_student_not_in_the_course_cannot_be_graded(client, classroom):
    response = grade(client, classroom, student_key="outsider")

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not enrolled in this course."


def test_other_teacher_cannot_grade(client, classroom):
    assert grade(client, classroom, user_key="other_teacher").status_code == 404


def test_student_cannot_grade(client, classroom):
    assert grade(client, classroom, user_key="classmate").status_code == 403


def test_grading_locks_the_submission(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom)

    unsubmit = client.post(
        f"/api/assignments/{classroom['assignment'].id}/submission/unsubmit",
        headers=auth_header(classroom["student"]),
    )

    assert unsubmit.status_code == 409


# ---------- students see only their own grade ----------


def test_student_sees_their_own_grade_and_feedback(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=18, feedback="Good work")

    response = my_grade(client, classroom)

    assert response.status_code == 200
    assert response.json()["score"] == 18
    assert response.json()["feedback"] == "Good work"


def test_classmate_does_not_see_my_grade(client, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=18)

    assert my_grade(client, classroom, user_key="classmate").json() is None


def test_grade_is_null_before_grading(client, classroom):
    response = my_grade(client, classroom)

    assert response.status_code == 200
    assert response.json() is None


def test_outsider_cannot_ask_for_a_grade(client, classroom):
    assert my_grade(client, classroom, user_key="outsider").status_code == 404


# ---------- recording changes for undo ----------


def test_first_grade_is_recorded_with_no_old_score(client, session, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=18, feedback="Nice job")

    [change] = recorded_changes(session)
    assert change.assignment_id == classroom["assignment"].id
    assert change.student_id == classroom["student"].id
    assert change.teacher_id == classroom["teacher"].id
    assert (change.old_score, change.old_feedback, change.old_graded_at) == (None, None, None)
    assert change.new_score == 18
    assert change.undone is False


def test_regrading_records_the_previous_grade(client, session, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=12, feedback="First try")
    first_graded_at = session.scalars(select(Grade)).one().graded_at

    grade(client, classroom, score=15, feedback="Re-marked")

    first, second = recorded_changes(session)
    assert first.old_score is None
    assert (second.old_score, second.old_feedback, second.new_score) == (12, "First try", 15)
    assert second.old_graded_at == first_graded_at


def test_each_regrade_is_recorded_in_order(client, session, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    for score in [10, 14, 17]:
        grade(client, classroom, score=score)

    changes = recorded_changes(session)
    assert [(c.old_score, c.new_score) for c in changes] == [(None, 10), (10, 14), (14, 17)]


def test_saving_the_same_grade_again_is_not_recorded(client, session, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=18, feedback="Nice job")

    response = grade(client, classroom, score=18, feedback="Nice job")

    assert response.status_code == 200
    assert len(recorded_changes(session)) == 1


def test_changing_only_the_feedback_is_recorded(client, session, classroom):
    upload(client, classroom)
    turn_in(client, classroom)
    grade(client, classroom, score=18, feedback="Nice job")

    grade(client, classroom, score=18, feedback="Nice job, but cite your sources")

    second = recorded_changes(session)[1]
    assert (second.old_score, second.old_feedback) == (18, "Nice job")


@pytest.mark.parametrize(
    "changes, expected_status",
    [
        (dict(user_key="classmate"), 403),  # a student
        (dict(user_key="other_teacher"), 404),  # a teacher outside the course
        (dict(student_key="outsider"), 404),  # a student outside the course
        (dict(score=100), 422),  # more than max points
    ],
)
def test_refused_grading_records_nothing(client, session, classroom, changes, expected_status):
    upload(client, classroom)
    turn_in(client, classroom)

    assert grade(client, classroom, **changes).status_code == expected_status
    assert recorded_changes(session) == []
