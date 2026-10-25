import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIN_SECRET_LENGTH = 32
# Example values from docs/instructions that must never be used as a real secret.
PLACEHOLDER_SECRETS = {"change-me", "paste-the-long-random-string-here"}

# Copy values from backend/.env into the environment. Variables that are already
# set (for example by the tests) are not overwritten.
load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_expire_minutes: int
    database_url: str
    upload_dir: Path


def load_settings() -> Settings:
    """Read settings from the environment and stop with a clear message if any are unsafe."""
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH or secret in PLACEHOLDER_SECRETS:
        # Never include the secret itself in an error message.
        raise RuntimeError(
            f"JWT_SECRET must be set to a random value of at least {MIN_SECRET_LENGTH} "
            "characters. See backend/.env.example."
        )

    try:
        expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    except ValueError:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be a whole number, e.g. 60.")
    if expire_minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be greater than 0.")

    database_url = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'classflow.db'}")
    # Uploaded files live here. It is git-ignored and never served directly.
    upload_dir = Path(os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "uploads")))

    return Settings(
        jwt_secret=secret,
        jwt_expire_minutes=expire_minutes,
        database_url=database_url,
        upload_dir=upload_dir,
    )


settings = load_settings()
