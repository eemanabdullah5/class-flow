import pytest

from app.graph import CycleError, dependency_order, find_cycle, find_path, would_create_cycle

# Variables ← Loops ← For loops, and Functions needs both Variables and Loops.
COURSE = {
    "Variables": [],
    "Loops": ["Variables"],
    "For loops": ["Loops"],
    "Functions": ["Variables", "Loops"],
}


def comes_before(order, first, second):
    return order.index(first) < order.index(second)


# ---------- find_path ----------


def test_finds_a_direct_dependency():
    assert find_path(COURSE, "Loops", "Variables") == ["Loops", "Variables"]


def test_finds_a_dependency_through_others():
    assert find_path(COURSE, "For loops", "Variables") == ["For loops", "Loops", "Variables"]


def test_no_path_against_the_arrows():
    assert find_path(COURSE, "Variables", "Loops") is None


def test_path_from_a_node_to_itself_is_just_that_node():
    assert find_path(COURSE, "Loops", "Loops") == ["Loops"]


def test_unknown_nodes_have_no_path():
    assert find_path(COURSE, "Recursion", "Variables") is None


# ---------- would_create_cycle ----------


def test_depending_on_itself_is_a_cycle():
    assert would_create_cycle(COURSE, "Loops", "Loops") == ["Loops", "Loops"]


def test_direct_two_way_dependency_is_a_cycle():
    assert would_create_cycle(COURSE, "Variables", "Loops") == ["Variables", "Loops", "Variables"]


def test_long_cycle_is_found_and_shown_in_full():
    assert would_create_cycle(COURSE, "Variables", "For loops") == [
        "Variables",
        "For loops",
        "Loops",
        "Variables",
    ]


def test_new_dependency_without_a_loop_is_fine():
    assert would_create_cycle(COURSE, "For loops", "Functions") is None
    assert would_create_cycle(COURSE, "Recursion", "Functions") is None


def test_diamond_shape_is_not_a_cycle():
    # Functions needs Variables twice over (directly and via Loops): allowed, not a loop.
    assert find_cycle(COURSE) is None


# ---------- find_cycle ----------


def test_graph_without_loops_has_no_cycle():
    assert find_cycle({}) is None
    assert find_cycle(COURSE) is None


@pytest.mark.parametrize(
    "graph",
    [
        {"A": ["A"]},
        {"A": ["B"], "B": ["A"]},
        {"A": ["B"], "B": ["C"], "C": ["A"], "D": []},
    ],
)
def test_cycle_is_found_and_starts_and_ends_on_the_same_node(graph):
    cycle = find_cycle(graph)

    assert cycle is not None
    assert cycle[0] == cycle[-1]
    for node, dependency in zip(cycle, cycle[1:]):
        assert dependency in graph[node]  # every step follows a real arrow


# ---------- dependency_order ----------


def test_order_puts_every_dependency_first():
    order = dependency_order(list(COURSE), COURSE)

    assert sorted(order) == sorted(COURSE)
    for node, dependencies in COURSE.items():
        for dependency in dependencies:
            assert comes_before(order, dependency, node)


def test_ties_keep_the_listed_order():
    nodes = ["C", "A", "B"]  # no dependencies at all

    assert dependency_order(nodes, {}) == ["C", "A", "B"]


def test_order_is_the_same_every_time():
    nodes = ["For loops", "Functions", "Loops", "Variables"]

    assert dependency_order(nodes, COURSE) == ["Variables", "Loops", "For loops", "Functions"]


def test_dependencies_outside_the_node_list_are_ignored():
    assert dependency_order(["Loops"], COURSE) == ["Loops"]


def test_order_with_a_loop_raises_cycle_error():
    with pytest.raises(CycleError) as error:
        dependency_order(["A", "B", "C"], {"A": ["B"], "B": ["A"]})

    assert set(error.value.cycle) == {"A", "B"}
