import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# Reads the "Authorization: Bearer <token>" header and adds the Authorize button to /docs.
# auto_error=False lets us send our own 401 message when the header is missing.
bearer_scheme = HTTPBearer(auto_error=False)


def not_logged_in(message: str = "Not logged in. Please log in.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Guard 1: who are you? Returns the logged-in user or stops with 401."""
    if credentials is None:
        raise not_logged_in()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise not_logged_in("Your session has expired. Please log in again.")
    except (jwt.InvalidTokenError, ValueError):
        raise not_logged_in("Invalid login token. Please log in again.")

    # Trust the database, not the token: the account may have been removed since login.
    user = db.get(User, user_id)
    if user is None:
        raise not_logged_in("Invalid login token. Please log in again.")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    """Guard 2 for teacher-only endpoints. Stops students with 403."""
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only teachers can do this.")
    return user


def require_student(user: User = Depends(get_current_user)) -> User:
    """Guard 2 for student-only endpoints. Stops teachers with 403."""
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can do this.")
    return user
