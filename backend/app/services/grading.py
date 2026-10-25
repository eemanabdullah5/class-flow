from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Grade, User, utc_now


def set_grade(
    db: Session, assignment_id: int, student_id: int, score: float, feedback: str | None, teacher: User
) -> Grade:
    """Create or change one student's grade.

    Every grade change goes through this one function, so the undo stack (Phase 7)
    only needs to be added here.
    """
    grade = db.scalars(
        select(Grade).where(Grade.assignment_id == assignment_id, Grade.student_id == student_id)
    ).first()
    if grade is None:
        grade = Grade(assignment_id=assignment_id, student_id=student_id)
        db.add(grade)

    grade.score = score
    grade.feedback = feedback
    grade.graded_by = teacher.id
    grade.graded_at = utc_now()
    db.commit()
    db.refresh(grade)
    return grade
