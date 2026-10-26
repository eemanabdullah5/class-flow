from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Grade, GradeChange, User, utc_now


def set_grade(
    db: Session, assignment_id: int, student_id: int, score: float, feedback: str | None, teacher: User
) -> Grade:
    """Create or change one student's grade, and record the old value for undo.

    Every grade the teacher gives goes through this one function, so every change
    lands on the undo stack. Saving the same score and feedback again changes
    nothing and is not recorded, so undo never seems to do nothing.
    """
    grade = db.scalars(
        select(Grade).where(Grade.assignment_id == assignment_id, Grade.student_id == student_id)
    ).first()
    if grade is not None and grade.score == score and grade.feedback == feedback:
        return grade

    # Write down the value before this change. All "old" fields stay empty for a first grade.
    db.add(
        GradeChange(
            assignment_id=assignment_id,
            student_id=student_id,
            teacher_id=teacher.id,
            old_score=grade.score if grade else None,
            old_feedback=grade.feedback if grade else None,
            old_graded_at=grade.graded_at if grade else None,
            new_score=score,
        )
    )

    if grade is None:
        grade = Grade(assignment_id=assignment_id, student_id=student_id)
        db.add(grade)

    grade.score = score
    grade.feedback = feedback
    grade.graded_by = teacher.id
    grade.graded_at = utc_now()
    db.commit()  # the change record and the new grade are saved together, or not at all
    db.refresh(grade)
    return grade
