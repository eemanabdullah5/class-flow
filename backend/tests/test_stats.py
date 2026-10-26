import statistics

import pytest

from app.stats import mean, pass_proportion, population_variance, summarize

MARKS = [40, 55, 70, 85, 100]


def test_mean():
    assert mean(MARKS) == 70


def test_population_variance_by_hand():
    # distances from 70: -30, -15, 0, 15, 30 -> squares 900, 225, 0, 225, 900 -> 2250 / 5
    assert population_variance(MARKS) == 450


def test_population_variance_matches_pythons_own():
    values = [12.5, 3, 7.25, 19, 0]

    assert population_variance(values) == pytest.approx(statistics.pvariance(values))


def test_everyone_the_same_has_zero_variance():
    assert population_variance([60, 60, 60]) == 0


def test_pass_proportion_counts_the_pass_mark_itself():
    assert pass_proportion(MARKS, 55) == pytest.approx(0.8)
    assert pass_proportion([49.9, 50], 50) == 0.5


def test_summary_of_a_class():
    assert summarize(MARKS, 50) == {
        "count": 5,
        "mean": 70,
        "minimum": 40,
        "maximum": 100,
        "variance": 450,
        "pass_proportion": 0.8,
    }


def test_summary_of_one_student():
    summary = summarize([65], 50)

    assert (summary["mean"], summary["variance"], summary["pass_proportion"]) == (65, 0, 1)


def test_summary_of_nobody_has_no_numbers():
    summary = summarize([], 50)

    assert summary["count"] == 0
    assert all(summary[key] is None for key in ["mean", "minimum", "maximum", "variance", "pass_proportion"])
