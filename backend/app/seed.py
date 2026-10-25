"""Create demo accounts and a sample course.

Run from the backend folder:  python -m app.seed

The password comes from DEMO_PASSWORD in backend/.env. If it is not set, a random
password is generated and printed once. Running the script again skips anything
that already exists, so it never creates duplicates or changes passwords.
"""

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, create_tables
from app.models import Course, Enrollment, User
from app.security import MAX_PASSWORD_BYTES, hash_password
from app.services.courses import generate_join_code

DEMO_TEACHER = {"email": "teacher@example.com", "full_name": "Demo Teacher", "role": "teacher"}
DEMO_STUDENTS = [
    {"email": "student1@example.com", "full_name": "Demo Student One", "role": "student"},
    {"email": "student2@example.com", "full_name": "Demo Student Two", "role": "student"},
]
DEMO_COURSE_TITLE = "Programming Fundamentals (Demo)"


def get_or_create_user(db: Session, details: dict, password: str) -> tuple[User, bool]:
    """Return (user, True) if newly created, or (existing user, False) if the email is taken."""
    user = db.scalars(select(User).where(User.email == details["email"])).first()
    if user is not None:
        return user, False
    user = User(**details, password_hash=hash_password(password))
    db.add(user)
    db.flush()  # gives the new user an id without committing yet
    return user, True


def seed(db: Session, password: str) -> list[str]:
    """Add the demo data and return a list of what happened, for printing."""
    report = []

    teacher, created = get_or_create_user(db, DEMO_TEACHER, password)
    report.append(f"{'Created' if created else 'Skipped (exists)'}: teacher {teacher.email}")

    students = []
    for details in DEMO_STUDENTS:
        student, created = get_or_create_user(db, details, password)
        students.append(student)
        report.append(f"{'Created' if created else 'Skipped (exists)'}: student {student.email}")

    course = db.scalars(
        select(Course).where(Course.title == DEMO_COURSE_TITLE, Course.teacher_id == teacher.id)
    ).first()
    if course is None:
        course = Course(
            title=DEMO_COURSE_TITLE,
            description="Sample course created by the seed script.",
            teacher_id=teacher.id,
            join_code=generate_join_code(db),
        )
        db.add(course)
        db.flush()
        report.append(f"Created: course '{course.title}' (join code {course.join_code})")
    else:
        report.append(f"Skipped (exists): course '{course.title}' (join code {course.join_code})")

    # Only student 1 is enrolled. Student 2 stays outside the course so you can
    # demo that non-members are blocked, and try joining with the code.
    first_student = students[0]
    enrolled = db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == course.id, Enrollment.student_id == first_student.id
        )
    ).first()
    if enrolled is None:
        db.add(Enrollment(course_id=course.id, student_id=first_student.id))
        report.append(f"Created: enrolled {first_student.email} in the course")

    db.commit()
    return report


def main():
    password = os.getenv("DEMO_PASSWORD", "")
    generated = False
    if not password:
        password = secrets.token_urlsafe(9)  # 12 random characters
        generated = True
    elif not 8 <= len(password.encode("utf-8")) <= MAX_PASSWORD_BYTES:
        raise SystemExit(f"DEMO_PASSWORD must be 8 to {MAX_PASSWORD_BYTES} characters long.")

    create_tables()
    with SessionLocal() as db:
        for line in seed(db, password):
            print(line)

    if generated:
        print("\nDEMO_PASSWORD is not set, so this random password was used for NEW accounts:")
        print(f"  {password}")
        print("It is shown only once. Accounts that already existed keep their old password.")
    else:
        print("\nNew accounts use the DEMO_PASSWORD from backend/.env.")


if __name__ == "__main__":
    main()
