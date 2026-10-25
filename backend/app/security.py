from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# bcrypt only works with the first 72 bytes of a password, so longer ones are refused.
MAX_PASSWORD_BYTES = 72
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Turn a plain password into a salted bcrypt hash that is safe to store."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain password against a stored hash."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False  # could never have been hashed, so it can't match
    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))


def create_access_token(user_id: int, role: str) -> str:
    """Make a signed login token that expires after JWT_EXPIRE_MINUTES."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # "subject": who the token belongs to
        "role": role,
        "iat": now,  # issued at
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Check the signature and expiry, then return the token's contents.

    Raises jwt.InvalidTokenError (or a subclass such as ExpiredSignatureError)
    if the token was changed, signed with another secret, has expired, or is
    missing the "exp" or "sub" fields.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub"]},  # a token without an expiry is never accepted
    )
