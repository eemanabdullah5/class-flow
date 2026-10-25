from datetime import datetime, timedelta, timezone

import pytest

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
