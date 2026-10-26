from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Grade, GradeChange, User, utc_now
from app.stack import Stack


def set_grade(
    db: Session, assignment_id: int, student_id: int, score: float, feedback: str | None, teacher: User
) -> Grade:
    """Create or change one student's grade, and record the old value for undo.

    Every grade the teacher gives goes through this one function, so every change
    lands on the undo stack. Saving the same score and feedback again changes
    nothing and is not recorded, so undo never seems to do nothing.
    The only other code that changes grades is undo_last_change() below.
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


def load_undo_stack(db: Session, teacher: User) -> Stack:
    """This teacher's changes that are not undone yet, with the newest on top.

    Each teacher only ever sees their own changes, so one teacher can never undo another's.
    """
    changes = db.scalars(
        select(GradeChange)
        .where(GradeChange.teacher_id == teacher.id, GradeChange.undone.is_(False))
        .order_by(GradeChange.id)  # oldest first, so the newest is pushed last and ends on top
    ).all()
    return Stack(changes)


def undo_last_change(db: Session, teacher: User) -> GradeChange | None:
    """Undo the teacher's newest grade change. Returns it, or None if there is nothing to undo.

    Restores the grade directly instead of calling set_grade(): otherwise undo would be
    recorded as a new change, and pressing undo again would just flip back (a redo).
    """
    stack = load_undo_stack(db, teacher)
    if stack.is_empty():
        return None
    change = stack.pop()

    grade = db.scalars(
        select(Grade).where(
            Grade.assignment_id == change.assignment_id, Grade.student_id == change.student_id
        )
    ).first()
    if change.old_score is None:
        # It was the first grade, so there was no grade before: remove it.
        # This also unlocks the submission, so the student can unsubmit again.
        if grade is not None:
            db.delete(grade)
    else:
        if grade is None:  # can't happen while every change is recorded, but stay safe
            grade = Grade(assignment_id=change.assignment_id, student_id=change.student_id)
            db.add(grade)
        grade.score = change.old_score
        grade.feedback = change.old_feedback
        grade.graded_by = teacher.id
        grade.graded_at = change.old_graded_at

    change.undone = True  # kept as history, but never undone (or redone) again
    db.commit()  # the restored grade and the undone mark are saved together
    return change
