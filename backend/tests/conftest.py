import os

# Must run before any "app" import: app.config checks JWT_SECRET as soon as it loads.
# This test-only value is not a real secret.
os.environ["JWT_SECRET"] = "test-secret-that-is-at-least-32-characters-long"

import pytest  # noqa: E402  (imports below must come after the line above)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (importing registers the models with Base)
from app.database import Base


@pytest.fixture
def session():
    """A brand-new, empty in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    yield db

    db.close()
    engine.dispose()
