from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def utc_now():
    return datetime.now(timezone.utc)


# Notes for reading this file:
# - Mapped[str] means NOT NULL; Mapped[Optional[str]] means the column may be empty (NULL).
# - ForeignKey("courses.id") means the value must match an existing course id.
# - ondelete="CASCADE" means: when the parent row is deleted, delete this row too.
#   Foreign keys to users have no ondelete, so a user who still owns data cannot be deleted.
# - relationship(...) does not create a column. It lets Python code follow a link,
#   e.g. course.assignments, without writing a JOIN.


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    courses_taught: Mapped[list["Course"]] = relationship(back_populates="teacher")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[Optional[str]] = mapped_column(Text)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    join_code: Mapped[str] = mapped_column(String(12), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    teacher: Mapped["User"] = relationship(back_populates="courses_taught")
    # cascade + passive_deletes: deleting a course removes its enrollments and
    # assignments, and the database's ON DELETE CASCADE does the actual work.
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", passive_deletes=True
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", passive_deletes=True
    )


class Enrollment(Base):
    """Links a student to a course (many-to-many between users and courses)."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_enrollment_course_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    course: Mapped["Course"] = relationship(back_populates="enrollments")
    student: Mapped["User"] = relationship(back_populates="enrollments")


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        # Only 'assignment' for the MVP; quiz/midterm/project are added later.
        CheckConstraint("category IN ('assignment')", name="ck_assignments_category"),
        CheckConstraint("max_points > 0", name="ck_assignments_max_points_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(150))
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20), default="assignment")
    max_points: Mapped[float] = mapped_column(Float)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    course: Mapped["Course"] = relationship(back_populates="assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", passive_deletes=True
    )
    grades: Mapped[list["Grade"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", passive_deletes=True
    )


class Submission(Base):
    """A student's uploaded file for one assignment. Starts as a draft until "mark as done"."""

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
        CheckConstraint("status IN ('draft', 'submitted')", name="ck_submissions_status"),
        CheckConstraint(
            f"file_size > 0 AND file_size <= {MAX_UPLOAD_BYTES}", name="ck_submissions_file_size"
        ),
        # A submitted row must record when it was submitted.
        CheckConstraint(
            "status = 'draft' OR submitted_at IS NOT NULL", name="ck_submissions_submitted_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    original_filename: Mapped[str] = mapped_column(String(255))  # shown to users only
    stored_filename: Mapped[str] = mapped_column(String(64), unique=True)  # random name on disk
    content_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship()


class Grade(Base):
    """Kept separate from Submission so offline work (e.g. a midterm) can be graded later."""

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_grade_assignment_student"),
        CheckConstraint("score >= 0", name="ck_grades_score_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    graded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    assignment: Mapped["Assignment"] = relationship(back_populates="grades")
    # Two foreign keys point at users, so we tell SQLAlchemy which one this link uses.
    student: Mapped["User"] = relationship(foreign_keys=[student_id])
