"""Course results: each student's weighted percentage, letter grade and pass/fail.

Loads a course's assignments, submissions and grades in three queries, then uses the
plain rules in app/scoring.py. Percentages are rounded to 1 decimal place first, and the
letter and pass/fail come from that rounded number, so what is shown always agrees.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assignment, Grade, Submission, utc_now
from app.scoring import (
    CATEGORIES,
    CATEGORY_WEIGHTS,
    category_totals,
    has_passed,
    item_points,
    letter_grade,
    weighted_percentage,
)


def describe(totals: dict) -> dict:
    """Turn {category: (earned, possible)} into what the API shows."""
    raw = weighted_percentage(totals)
    percentage = None if raw is None else round(raw, 1)
    categories = []
    for category in CATEGORIES:
        earned, possible = totals.get(category, (None, None))
        categories.append(
            {
                "category": category,
                "weight": CATEGORY_WEIGHTS[category],
                "earned": earned,
                "possible": possible,
                "percentage": None if not possible else round(100 * earned / possible, 1),
            }
        )
    return {
        "percentage": percentage,
        "letter": None if percentage is None else letter_grade(percentage),
        "passed": None if percentage is None else has_passed(percentage),
        "categories": categories,
    }


def course_results(db: Session, course_id: int, student_ids: list[int]) -> dict[int, dict]:
    """{student id: result} for these students of the course."""
    now = utc_now()
    assignments = db.scalars(select(Assignment).where(Assignment.course_id == course_id)).all()
    assignment_ids = [a.id for a in assignments]
    handed_in = {
        (s.assignment_id, s.student_id)
        for s in db.scalars(
            select(Submission).where(
                Submission.assignment_id.in_(assignment_ids), Submission.status == "submitted"
            )
        )
    }
    scores = {
        (g.assignment_id, g.student_id): g.score
        for g in db.scalars(select(Grade).where(Grade.assignment_id.in_(assignment_ids)))
    }

    results = {}
    for student_id in student_ids:
        items = [
            (
                a.category,
                item_points(
                    a.category,
                    a.max_points,
                    scores.get((a.id, student_id)),
                    past_due=a.due_at < now,
                    handed_in=(a.id, student_id) in handed_in,
                ),
            )
            for a in assignments
        ]
        results[student_id] = describe(category_totals(items))
    return results
