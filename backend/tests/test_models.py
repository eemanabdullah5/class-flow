from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Assignment,
    Course,
    Enrollment,
    Grade,
    GradeChange,
    Submission,
    Topic,
    TopicPrerequisite,
    User,
)

# ---------- helpers that build valid rows; each test changes one thing ----------


def make_user(session, email="ali@example.com", role="student"):
    user = User(email=email, full_name="Test User", password_hash="not-a-real-hash", role=role)
    session.add(user)
    session.commit()
    return user


def make_course(session, teacher, join_code="ABC123"):
    course = Course(title="Programming Fundamentals", teacher_id=teacher.id, join_code=join_code)
    session.add(course)
    session.commit()
    return course


def make_assignment(session, course, max_points=10):
    assignment = Assignment(
        course_id=course.id,
        title="Assignment 1",
        max_points=max_points,
        due_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(assignment)
    session.commit()
    return assignment


def new_submission(assignment, student, stored_filename="a1b2c3.pdf", **changes):
    fields = dict(
        assignment_id=assignment.id,
        student_id=student.id,
        original_filename="my work.pdf",
        stored_filename=stored_filename,
        content_type="application/pdf",
        file_size=2048,
    )
    fields.update(changes)
    return Submission(**fields)


@pytest.fixture
def setup(session):
    """A teacher, a student, a course and one assignment, ready to use."""
    teacher = make_user(session, email="teacher@example.com", role="teacher")
    student = make_user(session, email="student@example.com")
    course = make_course(session, teacher)
    assignment = make_assignment(session, course)
    return teacher, student, course, assignment


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


# ---------- users ----------


def test_user_can_be_saved_and_read_back(session):
    make_user(session)

    saved = session.scalars(select(User).where(User.email == "ali@example.com")).one()

    assert saved.id is not None
    assert saved.role == "student"
    assert saved.created_at is not None


def test_duplicate_email_is_rejected(session):
    make_user(session, email="same@example.com")

    with pytest.raises(IntegrityError):
        make_user(session, email="same@example.com")


def test_invalid_role_is_rejected(session):
    with pytest.raises(IntegrityError):
        make_user(session, role="admin")


def test_foreign_keys_are_switched_on(session):
    assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


# ---------- courses and enrollments ----------


def test_course_with_unknown_teacher_is_rejected(session):
    with pytest.raises(IntegrityError):
        session.add(Course(title="Ghost course", teacher_id=999, join_code="ZZZ999"))
        session.commit()


def test_duplicate_join_code_is_rejected(session, setup):
    teacher = setup[0]

    with pytest.raises(IntegrityError):
        make_course(session, teacher, join_code="ABC123")


def test_student_cannot_enroll_twice_in_same_course(session, setup):
    _, student, course, _ = setup
    session.add(Enrollment(course_id=course.id, student_id=student.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(Enrollment(course_id=course.id, student_id=student.id))
        session.commit()


def test_relationships_link_course_teacher_and_students(session, setup):
    teacher, student, course, assignment = setup
    session.add(Enrollment(course_id=course.id, student_id=student.id))
    session.commit()

    assert course.teacher.email == "teacher@example.com"
    assert teacher.courses_taught == [course]
    assert course.assignments == [assignment]
    assert [e.student for e in course.enrollments] == [student]


def test_deleting_course_deletes_its_enrollments_and_assignments(session, setup):
    _, student, course, _ = setup
    session.add(Enrollment(course_id=course.id, student_id=student.id))
    session.commit()

    session.delete(course)
    session.commit()

    assert count(session, Assignment) == 0
    assert count(session, Enrollment) == 0
    assert count(session, User) == 2  # people are not deleted with the course


# ---------- assignments ----------


def test_assignment_max_points_must_be_positive(session, setup):
    course = setup[2]

    with pytest.raises(IntegrityError):
        make_assignment(session, course, max_points=0)


@pytest.mark.parametrize("category", ["quiz", "assignment", "midterm", "project"])
def test_the_four_categories_are_allowed(session, setup, category):
    assignment = setup[3]
    assignment.category = category
    session.commit()

    assert assignment.category == category


def test_other_categories_are_rejected(session, setup):
    assignment = setup[3]
    assignment.category = "exam"

    with pytest.raises(IntegrityError):
        session.commit()


# ---------- submissions ----------


def test_new_submission_starts_as_draft(session, setup):
    _, student, _, assignment = setup
    session.add(new_submission(assignment, student))
    session.commit()

    submission = session.scalars(select(Submission)).one()
    assert submission.status == "draft"
    assert submission.submitted_at is None


def test_student_has_only_one_submission_per_assignment(session, setup):
    _, student, _, assignment = setup
    session.add(new_submission(assignment, student, stored_filename="first.pdf"))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(new_submission(assignment, student, stored_filename="second.pdf"))
        session.commit()


def test_submission_status_must_be_draft_or_submitted(session, setup):
    _, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(new_submission(assignment, student, status="late"))
        session.commit()


def test_submitted_status_requires_submitted_at(session, setup):
    _, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(new_submission(assignment, student, status="submitted", submitted_at=None))
        session.commit()


def test_file_larger_than_10_mb_is_rejected(session, setup):
    _, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(new_submission(assignment, student, file_size=10 * 1024 * 1024 + 1))
        session.commit()


# ---------- grades ----------


def test_grade_score_cannot_be_negative(session, setup):
    teacher, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(
            Grade(assignment_id=assignment.id, student_id=student.id, score=-1, graded_by=teacher.id)
        )
        session.commit()


def test_student_has_only_one_grade_per_assignment(session, setup):
    teacher, student, _, assignment = setup
    session.add(Grade(assignment_id=assignment.id, student_id=student.id, score=8, graded_by=teacher.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(
            Grade(assignment_id=assignment.id, student_id=student.id, score=9, graded_by=teacher.id)
        )
        session.commit()


# ---------- grade changes (undo stack) ----------


def new_change(assignment, student, teacher, **changes):
    fields = dict(
        assignment_id=assignment.id, student_id=student.id, teacher_id=teacher.id, new_score=8
    )
    fields.update(changes)
    return GradeChange(**fields)


def test_first_grade_change_has_no_old_values_and_is_not_undone(session, setup):
    teacher, student, _, assignment = setup
    session.add(new_change(assignment, student, teacher))
    session.commit()

    change = session.scalars(select(GradeChange)).one()
    assert change.old_score is None  # means "there was no grade before"
    assert change.old_feedback is None
    assert change.old_graded_at is None
    assert change.undone is False
    assert change.changed_at is not None


def test_grade_change_keeps_old_values(session, setup):
    teacher, student, _, assignment = setup
    graded_at = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    session.add(
        new_change(
            assignment, student, teacher, old_score=6, old_feedback="Good start", old_graded_at=graded_at
        )
    )
    session.commit()
    session.expire_all()

    change = session.scalars(select(GradeChange)).one()
    assert (change.old_score, change.old_feedback, change.old_graded_at) == (6, "Good start", graded_at)


def test_grade_change_scores_cannot_be_negative(session, setup):
    teacher, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(new_change(assignment, student, teacher, old_score=-1))
        session.commit()
    session.rollback()

    with pytest.raises(IntegrityError):
        session.add(new_change(assignment, student, teacher, new_score=-1))
        session.commit()


def test_grade_change_with_unknown_teacher_is_rejected(session, setup):
    _, student, _, assignment = setup

    with pytest.raises(IntegrityError):
        session.add(GradeChange(assignment_id=assignment.id, student_id=student.id, teacher_id=999, new_score=8))
        session.commit()


def test_deleting_assignment_deletes_its_grade_changes(session, setup):
    teacher, student, _, assignment = setup
    session.add(new_change(assignment, student, teacher))
    session.commit()

    session.delete(assignment)
    session.commit()

    assert count(session, GradeChange) == 0
    assert count(session, User) == 2


# ---------- topic prerequisites ----------


def two_topics(session, course):
    first, second = Topic(course_id=course.id, title="Variables"), Topic(course_id=course.id, title="Loops")
    session.add_all([first, second])
    session.commit()
    return first, second


def test_topic_cannot_be_its_own_prerequisite_in_the_database(session, setup):
    topic, _ = two_topics(session, setup[2])

    with pytest.raises(IntegrityError):
        session.add(TopicPrerequisite(topic_id=topic.id, prerequisite_id=topic.id))
        session.commit()


def test_same_prerequisite_arrow_cannot_be_saved_twice(session, setup):
    variables, loops = two_topics(session, setup[2])
    session.add(TopicPrerequisite(topic_id=loops.id, prerequisite_id=variables.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.add(TopicPrerequisite(topic_id=loops.id, prerequisite_id=variables.id))
        session.commit()

# ---------- UTC date-times ----------


def test_times_are_saved_and_loaded_as_utc(session, setup):
    assignment = setup[3]
    pakistan = timezone(timedelta(hours=5))
    assignment.due_at = datetime(2030, 1, 1, 23, 59, tzinfo=pakistan)
    session.commit()
    session.expire_all()  # force a fresh read from the database

    assert assignment.due_at == datetime(2030, 1, 1, 18, 59, tzinfo=timezone.utc)
    assert assignment.due_at.tzinfo == timezone.utc


def test_time_without_timezone_is_refused(session, setup):
    assignment = setup[3]
    assignment.due_at = datetime(2030, 1, 1, 23, 59)  # no timezone

    with pytest.raises(Exception, match="timezone"):
        session.commit()
