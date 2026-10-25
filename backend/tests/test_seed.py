import pytest
from sqlalchemy import func, select

from app.create_teacher import create_teacher
from app.models import Course, Enrollment, User
from app.security import verify_password
from app.seed import seed
from app.services.courses import JOIN_CODE_ALPHABET, JOIN_CODE_LENGTH, generate_join_code

DEMO_PASSWORD = "demo-pass-123"


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


# ---------- seed script ----------


def test_seed_creates_demo_teacher_students_course_and_enrollment(session):
    seed(session, DEMO_PASSWORD)

    teacher = session.scalars(select(User).where(User.role == "teacher")).one()
    assert teacher.email == "teacher@example.com"
    assert count(session, User) == 3
    course = session.scalars(select(Course)).one()
    assert course.teacher_id == teacher.id
    enrolled_emails = [e.student.email for e in course.enrollments]
    assert enrolled_emails == ["student1@example.com"]  # student 2 is left out on purpose


def test_seed_hashes_the_demo_password(session):
    seed(session, DEMO_PASSWORD)

    for user in session.scalars(select(User)):
        assert user.password_hash != DEMO_PASSWORD
        assert verify_password(DEMO_PASSWORD, user.password_hash)


def test_running_seed_twice_creates_no_duplicates_and_keeps_passwords(session):
    seed(session, DEMO_PASSWORD)
    report = seed(session, "a-different-password")

    assert count(session, User) == 3
    assert count(session, Course) == 1
    assert count(session, Enrollment) == 1
    assert all(line.startswith("Skipped") for line in report)
    teacher = session.scalars(select(User).where(User.role == "teacher")).one()
    assert verify_password(DEMO_PASSWORD, teacher.password_hash)  # unchanged


def test_demo_teacher_can_log_in_through_the_api(client, session):
    seed(session, DEMO_PASSWORD)

    response = client.post(
        "/api/auth/login", json={"email": "teacher@example.com", "password": DEMO_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "teacher"


# ---------- join codes ----------


def test_join_codes_use_the_readable_alphabet(session):
    code = generate_join_code(session)

    assert len(code) == JOIN_CODE_LENGTH
    assert all(character in JOIN_CODE_ALPHABET for character in code)


# ---------- create_teacher script ----------


def test_create_teacher_makes_a_teacher_account(session):
    teacher = create_teacher(session, "Khan@Uni.edu", "Ms. Khan", "teacherpass1")

    assert teacher.role == "teacher"
    assert teacher.email == "khan@uni.edu"
    assert verify_password("teacherpass1", teacher.password_hash)


def test_create_teacher_refuses_an_existing_email(session):
    create_teacher(session, "khan@uni.edu", "Ms. Khan", "teacherpass1")

    with pytest.raises(ValueError, match="already exists"):
        create_teacher(session, "KHAN@uni.edu", "Someone Else", "teacherpass2")


def test_create_teacher_uses_signup_rules_and_never_shows_the_password(session):
    with pytest.raises(ValueError) as error:
        create_teacher(session, "khan@uni.edu", "Ms. Khan", "Zq7!x")  # too short

    assert "password" in str(error.value)
    assert "Zq7!x" not in str(error.value)  # the typed password is not echoed back
    assert count(session, User) == 0
