"""How a student's course result is worked out. Plain Python, no database.

1. Each piece of work gives points: its score if graded, 0 if it is missing after the
   due date, or nothing yet (not due, or handed in and waiting for a grade).
2. Inside one category, points are added up: earned / possible (e.g. 27 / 40).
3. Categories are combined with fixed weights. A category with nothing counted yet is
   left out and the other weights are scaled up, so an early result isn't held down
   by work that hasn't happened yet.
"""

# Fixed weights (percent). They add up to 100.
CATEGORY_WEIGHTS = {"quiz": 10, "assignment": 10, "midterm": 30, "project": 50}
CATEGORIES = list(CATEGORY_WEIGHTS)
# Taken in class: there is nothing to upload, and the teacher enters the marks.
OFFLINE_CATEGORIES = {"midterm"}

PASS_PERCENT = 50  # absolute grading: 50% or more passes
# (lowest percent for the letter, letter), checked from the top down. Change the scale here only.
LETTER_SCALE = [(80, "A"), (70, "B"), (60, "C"), (50, "D"), (0, "F")]


def item_points(category, max_points, score, past_due, handed_in):
    """(earned, possible) for one piece of work, or None if it doesn't count yet.

    score: the grade, or None if not graded. handed_in: marked as done (submitted).
    Offline work (a midterm) only counts once the teacher enters a mark.
    """
    if score is not None:
        return (score, max_points)
    if category in OFFLINE_CATEGORIES:
        return None  # waiting for the teacher to enter marks
    if past_due and not handed_in:
        return (0, max_points)  # missing work counts as 0 after the deadline
    return None  # not due yet, or handed in and waiting for a grade


def category_totals(items):
    """Add up points per category. items: (category, (earned, possible) or None) pairs.

    Returns {category: (earned, possible)} for categories with at least one counted item.
    """
    totals = {}
    for category, points in items:
        if points is None:
            continue
        earned, possible = totals.get(category, (0, 0))
        totals[category] = (earned + points[0], possible + points[1])
    return totals


def weighted_percentage(totals):
    """The course percentage (0-100) from category totals, or None if nothing counts yet."""
    weighted_sum = 0
    weight_used = 0
    for category, (earned, possible) in totals.items():
        if possible > 0:
            weight = CATEGORY_WEIGHTS[category]
            weighted_sum += weight * earned / possible
            weight_used += weight
    if weight_used == 0:
        return None
    return 100 * weighted_sum / weight_used


def letter_grade(percent):
    for lowest, letter in LETTER_SCALE:
        if percent >= lowest:
            return letter
    return LETTER_SCALE[-1][1]


def has_passed(percent):
    return percent >= PASS_PERCENT
