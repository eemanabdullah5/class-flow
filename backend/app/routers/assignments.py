from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access import (
    get_assignment_for_member,
    get_assignment_for_owner,
    get_course_for_member,
    get_course_for_owner,
)
from app.database import get_db
from app.deps import get_current_user, require_teacher
from app.models import Assignment, Grade, Submission, User
from app.schemas import AssignmentCreate, AssignmentOut, AssignmentUpdate
from app.scoring import OFFLINE_CATEGORIES

router = APIRouter(tags=["assignments"])


@router.post(
    "/api/courses/{course_id}/assignments",
    response_model=AssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    course_id: int,
    data: AssignmentCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Only the teacher who owns the course."""
    get_course_for_owner(db, course_id, teacher)
    assignment = Assignment(course_id=course_id, **data.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/api/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(
    course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The course's teacher or an enrolled student. Soonest due date first."""
    get_course_for_member(db, course_id, user)
    return db.scalars(
        select(Assignment)
        .where(Assignment.course_id == course_id)
        .order_by(Assignment.due_at, Assignment.id)
    ).all()


@router.get("/api/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The course's teacher or an enrolled student. Anyone else gets 404."""
    return get_assignment_for_member(db, assignment_id, user)


@router.patch("/api/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Only the course's teacher. Fields left out of the body are not changed."""
    assignment = get_assignment_for_owner(db, assignment_id, teacher)
    changes = data.model_dump(exclude_unset=True)

    # Lowering max points must not leave an existing grade above the new maximum.
    if "max_points" in changes:
        highest_score = db.scalar(
            select(func.max(Grade.score)).where(Grade.assignment_id == assignment_id)
        )
        if highest_score is not None and changes["max_points"] < highest_score:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Max points can't be lower than an existing grade ({highest_score:g}).",
            )

    # In-class work (a midterm) has no uploads, so it can't take over files already handed in.
    if changes.get("category") in OFFLINE_CATEGORIES and assignment.category not in OFFLINE_CATEGORIES:
        has_files = db.scalar(select(func.count()).where(Submission.assignment_id == assignment_id))
        if has_files:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Students have already uploaded work, so this can't become in-class work.",
            )

    for field, value in changes.items():
        setattr(assignment, field, value)
    db.commit()
    db.refresh(assignment)
    return assignment
