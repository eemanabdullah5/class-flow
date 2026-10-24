import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import User


def make_user(email="ali@example.com", role="student"):
    return User(email=email, full_name="Ali Khan", password_hash="not-a-real-hash", role=role)


def test_user_can_be_saved_and_read_back(session):
    session.add(make_user())
    session.commit()

    saved = session.scalars(select(User).where(User.email == "ali@example.com")).one()

    assert saved.id is not None
    assert saved.role == "student"
    assert saved.created_at is not None


def test_duplicate_email_is_rejected(session):
    session.add(make_user(email="same@example.com"))
    session.commit()

    session.add(make_user(email="same@example.com"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_invalid_role_is_rejected(session):
    session.add(make_user(role="admin"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_are_switched_on(session):
    assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1
