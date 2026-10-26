from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_assignment_for_member, get_course_for_member
from app.database import get_db
from app.deps import get_current_user, require_student
from app.models import Assignment, Grade, Submission, User, utc_now
from app.schemas import MyWorkRow, SubmissionOut
from app.services.files import UploadRejected, delete_file, save_upload, stored_path

router = APIRouter(tags=["submissions"])

GRADED_LOCKED = "This work has been graded and can no longer be changed."


def find_submission(db: Session, assignment_id: int, student_id: int) -> Submission | None:
    return db.scalars(
        select(Submission).where(
            Submission.assignment_id == assignment_id, Submission.student_id == student_id
        )
    ).first()


def is_graded(db: Session, assignment_id: int, student_id: int) -> bool:
    grade = db.scalars(
        select(Grade).where(Grade.assignment_id == assignment_id, Grade.student_id == student_id)
    ).first()
    return grade is not None


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


@router.put("/api/assignments/{assignment_id}/submission", response_model=SubmissionOut)
def upload_submission(
    assignment_id: int,
    file: UploadFile = File(...),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Upload a file as a draft, or replace the file of an existing draft."""
    get_assignment_for_member(db, assignment_id, student)  # 404 unless enrolled
    if is_graded(db, assignment_id, student.id):
        raise conflict(GRADED_LOCKED)
    submission = find_submission(db, assignment_id, student.id)
    if submission is not None and submission.status == "submitted":
        raise conflict("Unsubmit first if you want to replace your file.")

    try:
        saved = save_upload(file)
    except UploadRejected as rejected:
        raise HTTPException(status_code=rejected.status_code, detail=rejected.message)

    old_file = None
    if submission is None:
        submission = Submission(assignment_id=assignment_id, student_id=student.id)
        db.add(submission)
    else:
        old_file = submission.stored_filename
    submission.stored_filename = saved.stored_filename
    submission.original_filename = saved.original_filename
    submission.content_type = saved.content_type
    submission.file_size = saved.file_size
    submission.uploaded_at = utc_now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(saved.stored_filename)  # don't keep a file the database doesn't know about
        raise
    if old_file:
        delete_file(old_file)
    db.refresh(submission)
    return submission


@router.post("/api/assignments/{assignment_id}/submission/turn-in", response_model=SubmissionOut)
def turn_in_submission(
    assignment_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    """Mark as done: the draft becomes submitted and the time is recorded."""
    get_assignment_for_member(db, assignment_id, student)
    submission = find_submission(db, assignment_id, student.id)
    if submission is None:
        raise conflict("Upload a file before marking the work as done.")
    if submission.status == "submitted":
        raise conflict("This work is already marked as done.")

    submission.status = "submitted"
    submission.submitted_at = utc_now()
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/api/assignments/{assignment_id}/submission/unsubmit", response_model=SubmissionOut)
def unsubmit_submission(
    assignment_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    """Back to draft so the file can be replaced. Not allowed once graded."""
    get_assignment_for_member(db, assignment_id, student)
    submission = find_submission(db, assignment_id, student.id)
    if submission is None or submission.status != "submitted":
        raise conflict("There is no submitted work to unsubmit.")
    if is_graded(db, assignment_id, student.id):
        raise conflict(GRADED_LOCKED)

    submission.status = "draft"
    submission.submitted_at = None
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/api/assignments/{assignment_id}/my-submission", response_model=SubmissionOut | None)
def read_my_submission(
    assignment_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)
):
    """The logged-in student's own submission, or null if nothing is uploaded yet.

    There is no student id in the URL, so it is impossible to ask for someone else's.
    """
    get_assignment_for_member(db, assignment_id, student)
    return find_submission(db, assignment_id, student.id)


@router.get("/api/submissions/{submission_id}/file")
def download_submission_file(
    submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Only the student who uploaded it or the course's teacher. Anyone else gets 404."""
    submission = db.get(Submission, submission_id)
    allowed = submission is not None and (
        submission.student_id == user.id or submission.assignment.course.teacher_id == user.id
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    path = stored_path(submission.stored_filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is missing.")

    # filename=... makes the browser download the file instead of opening it inside our
    # site, and nosniff stops it from guessing a different (possibly dangerous) type.
    return FileResponse(
        path,
        media_type=submission.content_type,
        filename=submission.original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/api/courses/{course_id}/my-work", response_model=list[MyWorkRow])
def read_my_work(course_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    """Every assignment in the course with the student's own status and grade, in one request.

    Only ever looks at the logged-in student's rows, so nobody else's work can leak.
    """
    get_course_for_member(db, course_id, student)
    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.course_id == course_id)
        .order_by(Assignment.due_at, Assignment.id)
    ).all()
    assignment_ids = [a.id for a in assignments]
    submissions = {
        s.assignment_id: s
        for s in db.scalars(
            select(Submission).where(
                Submission.student_id == student.id, Submission.assignment_id.in_(assignment_ids)
            )
        )
    }
    grades = {
        g.assignment_id: g
        for g in db.scalars(
            select(Grade).where(Grade.student_id == student.id, Grade.assignment_id.in_(assignment_ids))
        )
    }

    rows = []
    for assignment in assignments:
        submission = submissions.get(assignment.id)
        rows.append(
            MyWorkRow(
                assignment=assignment,
                submission_status=submission.status if submission else "none",
                is_late=submission.is_late if submission else False,
                grade=grades.get(assignment.id),
            )
        )
    return rows
