import pytest
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
