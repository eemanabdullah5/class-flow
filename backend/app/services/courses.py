import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course

# No 0/O or 1/I, so codes are easy to read out loud and type.
JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
JOIN_CODE_LENGTH = 6


def generate_join_code(db: Session) -> str:
    """Make a random course join code that no other course is using."""
    while True:
        code = "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_LENGTH))
        if db.scalars(select(Course).where(Course.join_code == code)).first() is None:
            return code
