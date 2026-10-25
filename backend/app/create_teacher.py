"""Add a real teacher account. Public sign-up can only create students.

Run from the backend folder:
    python -m app.create_teacher --email teacher@uni.edu --name "Ms. Khan"

The password is typed in the terminal (hidden, asked twice) and is never printed.
"""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, create_tables
from app.models import User
from app.schemas import RegisterRequest
from app.security import hash_password


def create_teacher(db: Session, email: str, full_name: str, password: str) -> User:
    """Validate the details with the same rules as sign-up, then save a teacher.

    Raises ValueError with a readable message if anything is wrong.
    """
    try:
        data = RegisterRequest(email=email, full_name=full_name, password=password)
    except ValidationError as error:
        # include_input=False keeps the password out of the error message.
        problems = [
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}"
            for e in error.errors(include_input=False)
        ]
        raise ValueError("; ".join(problems))

    if db.scalars(select(User).where(User.email == data.email)).first() is not None:
        raise ValueError(f"An account with the email {data.email} already exists.")

    teacher = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role="teacher",
    )
    db.add(teacher)
    db.commit()
    return teacher


def main():
    parser = argparse.ArgumentParser(description="Create a teacher account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help='Full name, in quotes if it has spaces')
    args = parser.parse_args()

    password = getpass("Password (8-72 characters, hidden while typing): ")
    if getpass("Type the password again: ") != password:
        raise SystemExit("The passwords did not match. Nothing was created.")

    create_tables()
    with SessionLocal() as db:
        try:
            teacher = create_teacher(db, args.email, args.name, password)
        except ValueError as error:
            raise SystemExit(f"Could not create teacher: {error}")

    print(f"Created teacher account: {teacher.email}")


if __name__ == "__main__":
    main()
