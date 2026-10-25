from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import User
from app.security import JWT_ALGORITHM, create_access_token, decode_access_token

VALID_SIGNUP = {
    "email": "Sara@Example.com",
    "full_name": "Sara Ahmed",
    "password": "strongpass123",
}


def register(client, **changes):
    return client.post("/api/auth/register", json={**VALID_SIGNUP, **changes})


def login(client, email="sara@example.com", password="strongpass123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------- register ----------


def test_register_creates_a_student(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "student"
    assert body["email"] == "sara@example.com"  # stored in lowercase
    assert "password" not in body and "password_hash" not in body


def test_register_cannot_choose_teacher_role(client, session):
    response = register(client, role="teacher")

    assert response.status_code == 422
    assert session.scalars(select(User)).first() is None  # nobody was created


def test_password_is_stored_as_a_hash(client, session):
    register(client)

    user = session.scalars(select(User)).one()
    assert user.password_hash != "strongpass123"
    assert user.password_hash.startswith("$2b$")


def test_duplicate_email_is_rejected_even_with_different_capitals(client):
    register(client)

    response = register(client, email="SARA@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists."


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "not-an-email"},
        {"full_name": "   "},
        {"password": "short"},  # under 8 characters
        {"password": "a" * 73},  # over 72 characters
        {"password": "🔒" * 20},  # 20 characters but 80 bytes
    ],
)
def test_invalid_signup_data_is_rejected(client, changes):
    assert register(client, **changes).status_code == 422


# ---------- login ----------


def test_login_returns_a_token_for_the_right_user(client):
    user_id = register(client).json()["id"]

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "sara@example.com"
    contents = decode_access_token(body["access_token"])
    assert contents["sub"] == str(user_id)
    assert contents["role"] == "student"


def test_login_email_is_not_case_sensitive(client):
    register(client)

    assert login(client, email="SARA@EXAMPLE.COM").status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_error(client):
    register(client)

    wrong_password = login(client, password="wrongpass123")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "Invalid email or password."}


# ---------- tokens ----------


def test_token_expires_after_the_configured_minutes():
    contents = decode_access_token(create_access_token(user_id=1, role="student"))

    lifetime = contents["exp"] - contents["iat"]
    assert lifetime == settings.jwt_expire_minutes * 60


def test_expired_token_is_rejected():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired = jwt.encode(
        {"sub": "1", "role": "student", "exp": past}, settings.jwt_secret, algorithm=JWT_ALGORITHM
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": "1", "role": "teacher"}, "some-other-secret-that-is-32-chars-long", algorithm=JWT_ALGORITHM
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)
