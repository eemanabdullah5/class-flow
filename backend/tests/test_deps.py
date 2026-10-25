from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.config import settings
from app.deps import require_student, require_teacher
from app.security import JWT_ALGORITHM
from tests.conftest import auth_header


def make_token(payload, secret=None):
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm=JWT_ALGORITHM)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def in_one_hour():
    return datetime.now(timezone.utc) + timedelta(hours=1)


# ---------- guard 1: get_current_user (tested through GET /api/auth/me) ----------


def test_me_returns_the_logged_in_user(client, make_user):
    student = make_user("student")

    response = client.get("/api/auth/me", headers=auth_header(student))

    assert response.status_code == 200
    assert response.json()["email"] == student.email
    assert response.json()["role"] == "student"


def test_no_token_gives_401(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not logged in. Please log in."


def test_expired_token_gives_401_with_session_expired_message(client, make_user):
    student = make_user("student")
    past = datetime.now(timezone.utc) - timedelta(minutes=1)

    response = client.get("/api/auth/me", headers=bearer(make_token({"sub": str(student.id), "exp": past})))

    assert response.status_code == 401
    assert response.json()["detail"] == "Your session has expired. Please log in again."


def test_token_signed_with_another_secret_gives_401(client, make_user):
    student = make_user("student")
    forged = make_token(
        {"sub": str(student.id), "role": "teacher", "exp": in_one_hour()},
        secret="an-attackers-guess-that-is-32-chars-long",
    )

    assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-real-token",
        make_token({"sub": "1"}),  # no expiry time: never accepted
        make_token({"sub": "abc", "exp": in_one_hour()}),  # user id is not a number
    ],
)
def test_broken_tokens_give_401(client, token):
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_token_of_deleted_user_gives_401(client, session, make_user):
    student = make_user("student")
    headers = auth_header(student)
    session.delete(student)
    session.commit()

    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_wrong_header_type_gives_401(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401


# ---------- guard 2: role checks ----------


def test_require_teacher_lets_teachers_through(make_user):
    teacher = make_user("teacher")

    assert require_teacher(teacher) is teacher


def test_require_teacher_blocks_students_with_403(make_user):
    with pytest.raises(HTTPException) as error:
        require_teacher(make_user("student"))

    assert error.value.status_code == 403


def test_require_student_lets_students_through(make_user):
    student = make_user("student")

    assert require_student(student) is student


def test_require_student_blocks_teachers_with_403(make_user):
    with pytest.raises(HTTPException) as error:
        require_student(make_user("teacher"))

    assert error.value.status_code == 403
