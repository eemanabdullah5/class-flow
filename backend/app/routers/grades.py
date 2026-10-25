from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_assignment_for_member, get_assignment_for_owner, is_enrolled
from app.database import get_db
from app.deps import require_student, require_teacher
from app.models import Enrollment, Grade, Submission, User, utc_now
from app.schemas import GradeOut, GradeSet, StudentWorkRow
from app.services.grading import set_grade

router = APIRouter(tags=["grades"])


@router.get("/api/assignments/{assignment_id}/submissions", response_model=list[StudentWorkRow])
def list_student_work(
    assignment_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    """Every enrolled student, including those who submitted nothing ("missing")."""
    assignment = get_assignment_for_owner(db, assignment_id, teacher)

    students = db.scalars(
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == assignment.course_id)
        .order_by(User.full_name)
    ).all()
    submissions = {
        s.student_id: s
        for s in db.scalars(select(Submission).where(Submission.assignment_id == assignment_id))
    }
    grades = {
        g.student_id: g for g in db.scalars(select(Grade).where(Grade.assignment_id == assignment_id))
    }

    rows = []
    for student in students:
        submission = submissions.get(student.id)
        rows.append(
            StudentWorkRow(
                student=student,
                status=submission.status if submission else "missing",
                submission=submission,
                grade=grades.get(student.id),
            )
        )
    return rows


@router.put("/api/assignments/{assignment_id}/grades/{student_id}", response_model=GradeOut)
def grade_student(
    assignment_id: int,
    student_id: int,
    data: GradeSet,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Give or change a grade. Only the course's teacher."""
    assignment = get_assignment_for_owner(db, assignment_id, teacher)

    if not is_enrolled(db, assignment.course_id, student_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student is not enrolled in this course."
        )
    if data.score > assignment.max_points:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Score can't be more than the assignment's max points ({assignment.max_points:g}).",
        )

    # Before the deadline a draft may still be in progress, so it can't be graded yet.
    # After the deadline, a draft that was never marked as done counts as not handed in.
    submission = db.scalars(
        select(Submission).where(
            Submission.assignment_id == assignment_id, Submission.student_id == student_id
        )
    ).first()
    if submission is not None and submission.status == "draft" and utc_now() < assignment.due_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student's work is still a draft. Wait until they mark it as done.",
        )

    return set_grade(db, assignment_id, student_id, data.score, data.feedback, teacher)


@router.get("/api/assignments/{assignment_id}/my-grade", response_model=GradeOut | None)
def read_my_grade(
    assignment_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    """The logged-in student's own grade, or null if not graded yet."""
    get_assignment_for_member(db, assignment_id, student)
    return db.scalars(
        select(Grade).where(Grade.assignment_id == assignment_id, Grade.student_id == student.id)
    ).first()
