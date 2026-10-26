from datetime import datetime, timedelta, timezone

from app.models import Assignment, Grade, Submission
from tests.conftest import auth_header


def my_work(client, classroom, user_key="student"):
    return client.get(
        f"/api/courses/{classroom['course'].id}/my-work", headers=auth_header(classroom[user_key])
    )


def add_submission(session, classroom, student_key="student", status="submitted"):
    session.add(
        Submission(
            assignment_id=classroom["assignment"].id,
            student_id=classroom[student_key].id,
            status=status,
            original_filename="hw.pdf",
            stored_filename=f"{student_key}.pdf",
            content_type="application/pdf",
            file_size=100,
            submitted_at=datetime.now(timezone.utc) if status == "submitted" else None,
        )
    )
    session.commit()


def test_lists_every_assignment_with_no_work_yet(client, session, classroom):
    session.add(
        Assignment(
            course_id=classroom["course"].id,
            title="Assignment 2",
            max_points=10,
            due_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    session.commit()

    response = my_work(client, classroom)

    assert response.status_code == 200
    rows = response.json()
    assert [row["assignment"]["title"] for row in rows] == ["Assignment 1", "Assignment 2"]
    assert all(row["submission_status"] == "none" and row["grade"] is None for row in rows)


def test_shows_my_status_and_grade(client, session, classroom):
    add_submission(session, classroom)
    session.add(
        Grade(
            assignment_id=classroom["assignment"].id,
            student_id=classroom["student"].id,
            score=17,
            graded_by=classroom["teacher"].id,
        )
    )
    session.commit()

    [row] = my_work(client, classroom).json()

    assert row["submission_status"] == "submitted"
    assert row["is_late"] is False
    assert row["grade"]["score"] == 17


def test_never_shows_a_classmates_work(client, session, classroom):
    add_submission(session, classroom, student_key="classmate")
    session.add(
        Grade(
            assignment_id=classroom["assignment"].id,
            student_id=classroom["classmate"].id,
            score=20,
            graded_by=classroom["teacher"].id,
        )
    )
    session.commit()

    [row] = my_work(client, classroom, user_key="student").json()

    assert row["submission_status"] == "none"
    assert row["grade"] is None


def test_outsider_and_teacher_cannot_use_it(client, classroom):
    assert my_work(client, classroom, user_key="outsider").status_code == 404
    assert my_work(client, classroom, user_key="teacher").status_code == 403
