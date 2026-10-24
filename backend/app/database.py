import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Where the database lives. Defaults to backend/classflow.db, no matter which
# folder the server is started from.
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'classflow.db'}")

# check_same_thread=False: FastAPI may use the connection from different threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Every model (table class) inherits from this."""


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores foreign keys unless this is switched on for every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def create_tables():
    """Create any tables that don't exist yet (existing tables are left untouched)."""
    from app import models  # noqa: F401  (importing registers the models with Base)

    Base.metadata.create_all(bind=engine)


def get_db():
    """Give one endpoint call its own session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
