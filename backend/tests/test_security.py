import pytest

from app.config import load_settings
from app.security import hash_password, verify_password

# ---------- password hashing ----------


def test_hash_is_not_the_plain_password():
    password_hash = hash_password("correct horse battery")

    assert password_hash != "correct horse battery"
    assert password_hash.startswith("$2b$")  # the bcrypt format marker


def test_correct_password_verifies():
    password_hash = hash_password("correct horse battery")

    assert verify_password("correct horse battery", password_hash) is True


def test_wrong_password_does_not_verify():
    password_hash = hash_password("correct horse battery")

    assert verify_password("wrong password", password_hash) is False


def test_same_password_gets_a_different_hash_each_time():
    first = hash_password("same password")
    second = hash_password("same password")

    assert first != second  # each hash has its own random salt
    assert verify_password("same password", first)
    assert verify_password("same password", second)


def test_password_longer_than_72_bytes_is_refused():
    with pytest.raises(ValueError):
        hash_password("a" * 73)


# ---------- settings ----------


def test_settings_load_with_a_long_enough_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.delenv("JWT_EXPIRE_MINUTES", raising=False)

    settings = load_settings()

    assert settings.jwt_expire_minutes == 60  # the default


def test_missing_secret_stops_the_app(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_placeholder_secret_from_example_file_is_too_short(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_placeholder_secret_from_instructions_is_refused_even_though_long(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "paste-the-long-random-string-here")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_expire_minutes_must_be_a_positive_number(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)

    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "soon")
    with pytest.raises(RuntimeError, match="JWT_EXPIRE_MINUTES"):
        load_settings()

    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "0")
    with pytest.raises(RuntimeError, match="JWT_EXPIRE_MINUTES"):
        load_settings()
