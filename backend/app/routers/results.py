from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_course_for_member, get_course_for_owner
from app.database import get_db
from app.deps import require_student, require_teacher
from app.models import Enrollment, User
from app.schemas import ClassResults, CourseResult
from app.scoring import LETTER_SCALE, PASS_PERCENT
from app.services.results import course_results
from app.stats import summarize

router = APIRouter(tags=["results"])


@router.get("/api/courses/{course_id}/my-result", response_model=CourseResult)
def read_my_result(course_id: int, student: User = Depends(require_student), db: Session = Depends(get_db)):
    """The logged-in student's weighted course result, with each category's part."""
    get_course_for_member(db, course_id, student)
    return course_results(db, course_id, [student.id])[student.id]


@router.get("/api/courses/{course_id}/results", response_model=ClassResults)
def read_class_results(course_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """Every enrolled student's result, plus class statistics. Only the course's teacher."""
    get_course_for_owner(db, course_id, teacher)
    students = db.scalars(
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
        .order_by(User.full_name, User.id)
    ).all()
    results = course_results(db, course_id, [s.id for s in students])
    # Students with nothing counted yet are listed, but left out of the statistics.
    percentages = [r["percentage"] for r in results.values() if r["percentage"] is not None]
    return {
        "pass_percent": PASS_PERCENT,
        "letter_scale": [{"lowest": lowest, "letter": letter} for lowest, letter in LETTER_SCALE],
        "students": [{"student": s, "result": results[s.id]} for s in students],
        "stats": summarize(percentages, PASS_PERCENT),
    }
