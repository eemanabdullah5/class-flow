"""Shared permission checks: "is this user allowed to see this course?"

Every router uses these instead of writing its own checks, so the rules live in one place.
Courses a user may not see get 404 (not 403), so outsiders can't even tell they exist.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, User

COURSE_NOT_FOUND = "Course not found."


def is_enrolled(db: Session, course_id: int, student_id: int) -> bool:
    enrollment = db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == course_id, Enrollment.student_id == student_id
        )
    ).first()
    return enrollment is not None


def get_course_for_member(db: Session, course_id: int, user: User) -> Course:
    """The course, if the user is its teacher or an enrolled student. Otherwise 404."""
    course = db.get(Course, course_id)
    allowed = course is not None and (
        course.teacher_id == user.id or is_enrolled(db, course_id, user.id)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COURSE_NOT_FOUND)
    return course


def get_course_for_owner(db: Session, course_id: int, teacher: User) -> Course:
    """The course, if this teacher owns it. Otherwise 404."""
    course = db.get(Course, course_id)
    if course is None or course.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COURSE_NOT_FOUND)
    return course
