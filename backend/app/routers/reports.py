"""The three course reports, written as raw SQL so each query can be read on its own.

Values are always passed as :parameters, never pasted into the SQL text,
so nothing a user types can change the query (no SQL injection).
Times are stored in UTC. bindparam() and .columns() use the same UTCDateTime type as
the models, so ":now" is compared in the stored format and times come back in UTC.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.access import get_course_for_owner
from app.database import get_db
from app.deps import require_teacher
from app.models import UTCDateTime, User, utc_now
from app.schemas import AssignmentReportRow, MissingLateRow, StudentReportRow

router = APIRouter(prefix="/api/courses/{course_id}/reports", tags=["reports"])

# 1. One row per assignment: how many handed in, late, missing and graded, and the scores.
#    Counts come from subqueries, so joining grades can't count a submission twice.
ASSIGNMENT_SUMMARY = (
    text("""
    SELECT a.id, a.title, a.category, a.max_points, a.due_at,
           (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = a.course_id) AS enrolled,
           (SELECT COUNT(*) FROM submissions s
             WHERE s.assignment_id = a.id AND s.status = 'submitted') AS turned_in,
           (SELECT COUNT(*) FROM submissions s
             WHERE s.assignment_id = a.id AND s.status = 'submitted'
               AND s.submitted_at > a.due_at) AS late,
           CASE
             WHEN a.category = 'midterm' THEN NULL  -- in class: nothing to hand in
             WHEN a.due_at >= :now THEN 0           -- not due yet, so nothing is missing
             ELSE (SELECT COUNT(*) FROM enrollments e
                    WHERE e.course_id = a.course_id
                      AND NOT EXISTS (SELECT 1 FROM submissions s
                                       WHERE s.assignment_id = a.id AND s.student_id = e.student_id
                                         AND s.status = 'submitted')
                      AND NOT EXISTS (SELECT 1 FROM grades g2
                                       WHERE g2.assignment_id = a.id AND g2.student_id = e.student_id))
           END AS missing,
           COUNT(g.id) AS graded,
           AVG(g.score) AS average_score,
           MIN(g.score) AS lowest_score,
           MAX(g.score) AS highest_score
      FROM assignments a
      LEFT JOIN grades g ON g.assignment_id = a.id
     WHERE a.course_id = :course_id
     GROUP BY a.id
     ORDER BY a.due_at, a.id
    """)
    .bindparams(bindparam("now", type_=UTCDateTime))
    .columns(due_at=UTCDateTime)
)

# 2. One row per enrolled student: work handed in, and the raw points of graded work.
#    (The weighted course percentage is worked out in app/services/results.py.)
STUDENT_PROGRESS = text("""
    SELECT u.id, u.full_name, u.email,
           (SELECT COUNT(*) FROM submissions s JOIN assignments a ON a.id = s.assignment_id
             WHERE a.course_id = e.course_id AND s.student_id = u.id
               AND s.status = 'submitted') AS turned_in,
           (SELECT COUNT(*) FROM submissions s JOIN assignments a ON a.id = s.assignment_id
             WHERE a.course_id = e.course_id AND s.student_id = u.id
               AND s.status = 'submitted' AND s.submitted_at > a.due_at) AS late,
           (SELECT COUNT(*) FROM grades g JOIN assignments a ON a.id = g.assignment_id
             WHERE a.course_id = e.course_id AND g.student_id = u.id) AS graded,
           (SELECT COALESCE(SUM(g.score), 0) FROM grades g JOIN assignments a ON a.id = g.assignment_id
             WHERE a.course_id = e.course_id AND g.student_id = u.id) AS points_earned,
           (SELECT COALESCE(SUM(a.max_points), 0) FROM grades g JOIN assignments a ON a.id = g.assignment_id
             WHERE a.course_id = e.course_id AND g.student_id = u.id) AS points_possible
      FROM enrollments e
      JOIN users u ON u.id = e.student_id
     WHERE e.course_id = :course_id
     ORDER BY u.full_name, u.id
""")

# 3. Every piece of work past its due date that is missing (not handed in and not graded)
#    or was handed in late. In-class work (midterm) can't be missing or late.
MISSING_AND_LATE = (
    text("""
    SELECT u.id AS student_id, u.full_name AS student_name,
           a.id AS assignment_id, a.title AS assignment_title, a.category, a.due_at,
           s.submitted_at,
           CASE WHEN s.status = 'submitted' THEN 'late' ELSE 'missing' END AS problem
      FROM assignments a
      JOIN enrollments e ON e.course_id = a.course_id
      JOIN users u ON u.id = e.student_id
      LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = u.id
      LEFT JOIN grades g ON g.assignment_id = a.id AND g.student_id = u.id
     WHERE a.course_id = :course_id
       AND a.category <> 'midterm'
       AND a.due_at < :now
       AND (
             (s.status = 'submitted' AND s.submitted_at > a.due_at)
          OR (g.id IS NULL AND (s.id IS NULL OR s.status = 'draft'))
           )
     ORDER BY a.due_at, a.id, u.full_name
    """)
    .bindparams(bindparam("now", type_=UTCDateTime))
    .columns(due_at=UTCDateTime, submitted_at=UTCDateTime)
)


@router.get("/assignments", response_model=list[AssignmentReportRow])
def assignment_summary(course_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """Report 1: per assignment, how the class is doing. Only the course's teacher."""
    get_course_for_owner(db, course_id, teacher)
    return db.execute(ASSIGNMENT_SUMMARY, {"course_id": course_id, "now": utc_now()}).mappings().all()


@router.get("/students", response_model=list[StudentReportRow])
def student_progress(course_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """Report 2: per student, work handed in and points so far. Only the course's teacher."""
    get_course_for_owner(db, course_id, teacher)
    return db.execute(STUDENT_PROGRESS, {"course_id": course_id}).mappings().all()


@router.get("/missing-late", response_model=list[MissingLateRow])
def missing_and_late(course_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """Report 3: who is missing work or handed it in late. Only the course's teacher."""
    get_course_for_owner(db, course_id, teacher)
    return db.execute(MISSING_AND_LATE, {"course_id": course_id, "now": utc_now()}).mappings().all()
