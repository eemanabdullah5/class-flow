import pytest

from tests.conftest import auth_header


@pytest.fixture
def people(make_user):
    """Two teachers and two students, so we can test who sees what."""
    return {
        "teacher": make_user("teacher"),
        "other_teacher": make_user("teacher"),
        "student": make_user("student"),
        "other_student": make_user("student"),
    }


def create_course(client, teacher, title="Programming Fundamentals"):
    response = client.post("/api/courses", json={"title": title}, headers=auth_header(teacher))
    assert response.status_code == 201
    return response.json()


def join(client, student, code):
    return client.post("/api/courses/join", json={"join_code": code}, headers=auth_header(student))


# ---------- creating courses ----------


def test_teacher_creates_a_course_with_a_join_code(client, people):
    response = client.post(
        "/api/courses",
        json={"title": "  OOP  ", "description": "Classes and objects"},
        headers=auth_header(people["teacher"]),
    )

    assert response.status_code == 201
    course = response.json()
    assert course["title"] == "OOP"  # extra spaces removed
    assert len(course["join_code"]) == 6
    assert course["teacher_name"] == people["teacher"].full_name


def test_student_cannot_create_a_course(client, people):
    response = client.post(
        "/api/courses", json={"title": "Hacked"}, headers=auth_header(people["student"])
    )

    assert response.status_code == 403


def test_creating_a_course_requires_login(client):
    assert client.post("/api/courses", json={"title": "No login"}).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"title": "   "},  # blank
        {"title": "x" * 151},  # too long
        {"title": "Sneaky", "teacher_id": 999},  # can't pick the owner
        {"title": "Sneaky", "join_code": "AAAAAA"},  # can't pick the code
    ],
)
def test_invalid_course_data_is_rejected(client, people, body):
    response = client.post("/api/courses", json=body, headers=auth_header(people["teacher"]))

    assert response.status_code == 422


# ---------- listing courses ----------


def test_teacher_sees_only_their_own_courses(client, people):
    create_course(client, people["teacher"], "Mine")
    create_course(client, people["other_teacher"], "Not mine")

    response = client.get("/api/courses", headers=auth_header(people["teacher"]))

    assert [c["title"] for c in response.json()] == ["Mine"]


def test_student_sees_only_courses_they_joined(client, people):
    joined = create_course(client, people["teacher"], "Joined")
    create_course(client, people["teacher"], "Not joined")
    join(client, people["student"], joined["join_code"])

    response = client.get("/api/courses", headers=auth_header(people["student"]))

    assert [c["title"] for c in response.json()] == ["Joined"]


def test_new_student_has_an_empty_course_list(client, people):
    response = client.get("/api/courses", headers=auth_header(people["student"]))

    assert response.status_code == 200
    assert response.json() == []


# ---------- joining with a code ----------


def test_student_joins_with_code_ignoring_case_and_spaces(client, people):
    course = create_course(client, people["teacher"])

    response = join(client, people["student"], f"  {course['join_code'].lower()} ")

    assert response.status_code == 201
    assert response.json()["id"] == course["id"]


def test_wrong_code_gives_a_clear_error(client, people):
    response = join(client, people["student"], "NOPE99")

    assert response.status_code == 404
    assert "No course found with that code" in response.json()["detail"]


def test_joining_twice_is_rejected(client, people):
    course = create_course(client, people["teacher"])
    join(client, people["student"], course["join_code"])

    response = join(client, people["student"], course["join_code"])

    assert response.status_code == 409
    assert response.json()["detail"] == "You are already enrolled in this course."


def test_teacher_cannot_join_a_course(client, people):
    course = create_course(client, people["other_teacher"])

    assert join(client, people["teacher"], course["join_code"]).status_code == 403


# ---------- viewing one course ----------


def test_owner_and_enrolled_student_can_view_the_course(client, people):
    course = create_course(client, people["teacher"])
    join(client, people["student"], course["join_code"])

    for user in (people["teacher"], people["student"]):
        response = client.get(f"/api/courses/{course['id']}", headers=auth_header(user))
        assert response.status_code == 200


@pytest.mark.parametrize("outsider", ["other_teacher", "other_student"])
def test_outsiders_get_404_for_a_course_they_dont_belong_to(client, people, outsider):
    course = create_course(client, people["teacher"])

    response = client.get(f"/api/courses/{course['id']}", headers=auth_header(people[outsider]))

    assert response.status_code == 404  # same answer as a course that doesn't exist


def test_course_that_does_not_exist_gives_404(client, people):
    response = client.get("/api/courses/9999", headers=auth_header(people["teacher"]))

    assert response.status_code == 404


# ---------- class roster ----------


def test_owner_sees_the_enrolled_students(client, people):
    course = create_course(client, people["teacher"])
    join(client, people["student"], course["join_code"])

    response = client.get(
        f"/api/courses/{course['id']}/students", headers=auth_header(people["teacher"])
    )

    assert response.status_code == 200
    assert [s["email"] for s in response.json()] == [people["student"].email]
    assert "password_hash" not in response.json()[0]


def test_other_teacher_cannot_see_the_roster(client, people):
    course = create_course(client, people["teacher"])

    response = client.get(
        f"/api/courses/{course['id']}/students", headers=auth_header(people["other_teacher"])
    )

    assert response.status_code == 404


def test_enrolled_student_cannot_see_the_roster(client, people):
    course = create_course(client, people["teacher"])
    join(client, people["student"], course["join_code"])

    response = client.get(
        f"/api/courses/{course['id']}/students", headers=auth_header(people["student"])
    )

    assert response.status_code == 403
