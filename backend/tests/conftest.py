import os

# Must run before any "app" import: app.config checks JWT_SECRET as soon as it loads.
# This test-only value is not a real secret.
os.environ["JWT_SECRET"] = "test-secret-that-is-at-least-32-characters-long"

import pytest  # noqa: E402  (imports below must come after the line above)
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402, F401  (importing registers the models with Base)
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def session():
    """A brand-new, empty in-memory database for each test."""
    # StaticPool keeps one shared connection, so the in-memory database survives
    # across the test client's requests instead of vanishing between them.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    yield db

    db.close()
    engine.dispose()


@pytest.fixture
def client(session):
    """Sends fake HTTP requests to the app, using the test database instead of classflow.db."""

    def use_test_database():
        yield session

    app.dependency_overrides[get_db] = use_test_database
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(session):
    """Create a user straight in the test database: make_user("teacher") or make_user("student")."""
    from app.models import User

    created = 0

    def _make_user(role="student", email=None):
        nonlocal created
        created += 1
        user = User(
            email=email or f"{role}{created}@example.com",
            full_name=f"Test {role.title()} {created}",
            password_hash="not-used-in-these-tests",
            role=role,
        )
        session.add(user)
        session.commit()
        return user

    return _make_user


def auth_header(user):
    """The header a logged-in user's browser would send with each request."""
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


@pytest.fixture(autouse=True)
def temporary_upload_dir(tmp_path, monkeypatch):
    """Every test saves uploads in its own temporary folder, never in backend/uploads/."""
    from dataclasses import replace

    from app.services import files

    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(files, "settings", replace(files.settings, upload_dir=upload_dir))
    return upload_dir
