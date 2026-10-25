import bcrypt

# bcrypt only works with the first 72 bytes of a password, so longer ones are refused.
MAX_PASSWORD_BYTES = 72


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
