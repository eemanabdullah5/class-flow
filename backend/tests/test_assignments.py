from datetime import datetime, timedelta, timezone

import pytest

from app.models import Course, Enrollment, Grade
from tests.conftest import auth_header


def next_week():
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


@pytest.fixture
def world(session, make_user):
    """A course with its teacher and one enrolled student, plus two outsiders."""
    teacher = make_user("teacher")
    student = make_user("student")
    course = Course(title="Programming Fundamentals", teacher_id=teacher.id, join_code="PF1234")
    session.add(course)
    session.commit()
    session.add(Enrollment(course_id=course.id, student_id=student.id))
    session.commit()
    return {
        "course": course,
        "teacher": teacher,
        "student": student,
        "other_teacher": make_user("teacher"),
        "outsider": make_user("student"),
    }


def valid_assignment(**changes):
    body = {
        "title": "Assignment 1",
        "instructions": "Write a calculator program.",
        "max_points": 20,
        "due_at": next_week(),
    }
    body.update(changes)
    return body


def create(client, world, user_key="teacher", **changes):
    return client.post(
        f"/api/courses/{world['course'].id}/assignments",
        json=valid_assignment(**changes),
        headers=auth_header(world[user_key]),
    )


# ---------- creating ----------


def test_teacher_creates_an_assignment(client, world):
    response = create(client, world)

    assert response.status_code == 201
    assignment = response.json()
    assert assignment["title"] == "Assignment 1"
    assert assignment["category"] == "assignment"
    assert assignment["course_id"] == world["course"].id


def test_due_date_is_converted_to_utc(client, world):
    # 23:59 in Pakistan (UTC+5) is 18:59 UTC.
    response = create(client, world, due_at="2030-01-01T23:59:00+05:00")

    assert response.status_code == 201
    assert response.json()["due_at"] == "2030-01-01T18:59:00Z"


def test_student_cannot_create_an_assignment(client, world):
    assert create(client, world, user_key="student").status_code == 403


def test_other_teacher_cannot_add_to_a_course_they_dont_own(client, world):
    assert create(client, world, user_key="other_teacher").status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "  "},
        {"max_points": 0},
        {"max_points": -5},
        {"max_points": 1001},
        {"due_at": "2020-01-01T10:00:00Z"},  # in the past
        {"due_at": "2030-01-01T10:00:00"},  # no timezone
        {"due_at": "next friday"},
        {"category": "exam"},  # not one of the four categories
        {"course_id": 999},  # comes from the URL only
    ],
)
def test_invalid_assignment_data_is_rejected(client, world, changes):
    assert create(client, world, **changes).status_code == 422


def test_due_date_is_required(client, world):
    body = valid_assignment()
    del body["due_at"]

    response = client.post(
        f"/api/courses/{world['course'].id}/assignments",
        json=body,
        headers=auth_header(world["teacher"]),
    )

    assert response.status_code == 422


# ---------- listing and viewing ----------


def test_teacher_and_enrolled_student_see_assignments_soonest_first(client, world):
    later = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    create(client, world, title="Due later", due_at=later)
    create(client, world, title="Due sooner")

    for user_key in ("teacher", "student"):
        response = client.get(
            f"/api/courses/{world['course'].id}/assignments", headers=auth_header(world[user_key])
        )
        assert response.status_code == 200
        assert [a["title"] for a in response.json()] == ["Due sooner", "Due later"]


@pytest.mark.parametrize("user_key", ["outsider", "other_teacher"])
def test_outsiders_cannot_list_or_view_assignments(client, world, user_key):
    assignment_id = create(client, world).json()["id"]
    headers = auth_header(world[user_key])

    assert client.get(f"/api/courses/{world['course'].id}/assignments", headers=headers).status_code == 404
    assert client.get(f"/api/assignments/{assignment_id}", headers=headers).status_code == 404


def test_enrolled_student_can_view_one_assignment(client, world):
    assignment_id = create(client, world).json()["id"]

    response = client.get(f"/api/assignments/{assignment_id}", headers=auth_header(world["student"]))

    assert response.status_code == 200
    assert response.json()["title"] == "Assignment 1"


def test_assignment_that_does_not_exist_gives_404(client, world):
    response = client.get("/api/assignments/9999", headers=auth_header(world["teacher"]))

    assert response.status_code == 404


# ---------- editing ----------


def test_teacher_edits_only_the_fields_sent(client, world):
    assignment_id = create(client, world).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}",
        json={"title": "Assignment 1 (updated)"},
        headers=auth_header(world["teacher"]),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Assignment 1 (updated)"
    assert response.json()["max_points"] == 20  # unchanged


@pytest.mark.parametrize("field", ["title", "max_points", "due_at"])
def test_required_fields_cannot_be_emptied_with_null(client, world, field):
    assignment_id = create(client, world).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={field: None}, headers=auth_header(world["teacher"])
    )

    assert response.status_code == 422
    assert "cannot be empty" in str(response.json()["detail"])


def test_instructions_can_be_cleared_with_null(client, world):
    assignment_id = create(client, world, instructions="Read chapter 2").json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={"instructions": None}, headers=auth_header(world["teacher"])
    )

    assert response.status_code == 200
    assert response.json()["instructions"] is None


def test_student_cannot_edit_an_assignment(client, world):
    assignment_id = create(client, world).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}", json={"title": "Easy A"}, headers=auth_header(world["student"])
    )

    assert response.status_code == 403


def test_other_teacher_cannot_edit_an_assignment(client, world):
    assignment_id = create(client, world).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}",
        json={"title": "Mine now"},
        headers=auth_header(world["other_teacher"]),
    )

    assert response.status_code == 404


def test_cannot_move_due_date_into_the_past(client, world):
    assignment_id = create(client, world).json()["id"]

    response = client.patch(
        f"/api/assignments/{assignment_id}",
        json={"due_at": "2020-01-01T10:00:00Z"},
        headers=auth_header(world["teacher"]),
    )

    assert response.status_code == 422


def test_max_points_cannot_drop_below_an_existing_grade(client, session, world):
    assignment_id = create(client, world).json()["id"]
    session.add(
        Grade(
            assignment_id=assignment_id,
            student_id=world["student"].id,
            score=15,
            graded_by=world["teacher"].id,
        )
    )
    session.commit()
    headers = auth_header(world["teacher"])

    too_low = client.patch(f"/api/assignments/{assignment_id}", json={"max_points": 10}, headers=headers)
    fine = client.patch(f"/api/assignments/{assignment_id}", json={"max_points": 15}, headers=headers)

    assert too_low.status_code == 409
    assert "15" in too_low.json()["detail"]
    assert fine.status_code == 200
