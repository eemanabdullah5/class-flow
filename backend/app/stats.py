"""Class statistics, written out by hand so each formula is easy to follow. Plain Python."""


def mean(values):
    return sum(values) / len(values)


def population_variance(values):
    """The average squared distance from the mean: sum((x - mean)^2) / n.

    "Population" because we divide by n (the whole class), not n - 1 (a sample).
    """
    average = mean(values)
    return sum((x - average) ** 2 for x in values) / len(values)


def pass_proportion(values, pass_mark):
    """The share of values at or above pass_mark, from 0.0 to 1.0."""
    return sum(1 for x in values if x >= pass_mark) / len(values)


def summarize(values, pass_mark):
    """Count, mean, min, max, population variance and pass proportion.

    With no values everything except count is None, because an average of nothing doesn't exist.
    """
    if not values:
        return {
            "count": 0,
            "mean": None,
            "minimum": None,
            "maximum": None,
            "variance": None,
            "pass_proportion": None,
        }
    return {
        "count": len(values),
        "mean": mean(values),
        "minimum": min(values),
        "maximum": max(values),
        "variance": population_variance(values),
        "pass_proportion": pass_proportion(values, pass_mark),
    }
