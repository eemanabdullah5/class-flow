import pytest

from app.scoring import (
    CATEGORY_WEIGHTS,
    category_totals,
    has_passed,
    item_points,
    letter_grade,
    weighted_percentage,
)


def test_weights_add_up_to_100():
    assert sum(CATEGORY_WEIGHTS.values()) == 100


# ---------- item_points: what one piece of work counts as ----------


@pytest.mark.parametrize(
    "score, past_due, handed_in, expected",
    [
        (18, False, True, (18, 20)),  # graded counts, whatever else is true
        (0, True, False, (0, 20)),  # missing work the teacher gave 0
        (None, True, False, (0, 20)),  # missing after the deadline counts as 0
        (None, False, False, None),  # not due yet
        (None, True, True, None),  # handed in, waiting for a grade
        (None, False, True, None),
    ],
)
def test_item_points_for_uploaded_work(score, past_due, handed_in, expected):
    assert item_points("assignment", 20, score, past_due, handed_in) == expected


def test_ungraded_midterm_doesnt_count_even_after_the_date():
    assert item_points("midterm", 50, None, past_due=True, handed_in=False) is None
    assert item_points("midterm", 50, 35, past_due=True, handed_in=False) == (35, 50)


# ---------- category_totals ----------


def test_points_are_added_up_per_category():
    items = [
        ("quiz", (8, 10)),
        ("quiz", (5, 10)),
        ("assignment", (18, 20)),
        ("project", None),  # not counted yet
    ]

    assert category_totals(items) == {"quiz": (13, 20), "assignment": (18, 20)}


def test_bigger_items_weigh_more_inside_a_category():
    # By points, not by averaging percentages: 9/10 and 10/40 give 19/50 = 38%, not 61%.
    assert category_totals([("quiz", (9, 10)), ("quiz", (10, 40))]) == {"quiz": (19, 50)}


# ---------- weighted_percentage ----------


def test_all_categories_use_the_fixed_weights():
    totals = {"quiz": (10, 10), "assignment": (0, 10), "midterm": (15, 30), "project": (40, 50)}

    # 10% * 100 + 10% * 0 + 30% * 50 + 50% * 80 = 10 + 0 + 15 + 40
    assert weighted_percentage(totals) == pytest.approx(65)


def test_missing_categories_are_left_out_and_the_rest_scaled_up():
    # Only quiz (10) and midterm (30) so far: (10 * 1.0 + 30 * 0.5) / 40 = 62.5%
    assert weighted_percentage({"quiz": (10, 10), "midterm": (25, 50)}) == pytest.approx(62.5)


def test_one_category_alone_is_just_its_own_percentage():
    assert weighted_percentage({"assignment": (15, 20)}) == pytest.approx(75)


def test_nothing_counted_gives_no_percentage():
    assert weighted_percentage({}) is None


# ---------- letters and passing ----------


@pytest.mark.parametrize(
    "percent, letter",
    [(100, "A"), (80, "A"), (79.9, "B"), (70, "B"), (69.99, "C"), (60, "C"), (59, "D"), (50, "D"), (49.9, "F"), (0, "F")],
)
def test_letter_grade_scale(percent, letter):
    assert letter_grade(percent) == letter


@pytest.mark.parametrize("percent, passed", [(50, True), (49.99, False), (100, True), (0, False)])
def test_pass_is_50_percent(percent, passed):
    assert has_passed(percent) is passed
