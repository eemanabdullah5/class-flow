from app.tree import build_tree, would_create_loop

# Items are (id, parent_id) pairs, so the tests stay short.
ITEM_ID = lambda item: item[0]  # noqa: E731
PARENT_ID = lambda item: item[1]  # noqa: E731


def shape(nodes):
    """Turn built nodes into {id: {child id: {...}}} so whole trees are easy to compare."""
    return {node["item"][0]: shape(node["children"]) for node in nodes}


# ---------- build_tree ----------


def test_empty_list_gives_empty_tree():
    assert build_tree([], ITEM_ID, PARENT_ID) == []


def test_items_without_parents_are_all_top_level():
    assert shape(build_tree([(1, None), (2, None)], ITEM_ID, PARENT_ID)) == {1: {}, 2: {}}


def test_children_are_nested_under_their_parents():
    items = [(1, None), (2, 1), (3, 2), (4, 1), (5, None)]

    assert shape(build_tree(items, ITEM_ID, PARENT_ID)) == {1: {2: {3: {}}, 4: {}}, 5: {}}


def test_child_listed_before_its_parent_still_nests():
    assert shape(build_tree([(2, 1), (1, None)], ITEM_ID, PARENT_ID)) == {1: {2: {}}}


def test_children_keep_the_order_of_the_list():
    nodes = build_tree([(1, None), (3, 1), (2, 1)], ITEM_ID, PARENT_ID)

    assert [child["item"][0] for child in nodes[0]["children"]] == [3, 2]


def test_item_with_missing_parent_is_shown_at_top_level():
    assert shape(build_tree([(2, 99)], ITEM_ID, PARENT_ID)) == {2: {}}


# ---------- would_create_loop ----------

# 1
# ├── 2
# │   └── 3
# └── 4
PARENT_OF = {1: None, 2: 1, 3: 2, 4: 1}


def test_moving_under_itself_is_a_loop():
    assert would_create_loop(PARENT_OF, 2, 2)


def test_moving_under_own_child_or_grandchild_is_a_loop():
    assert would_create_loop(PARENT_OF, 1, 2)
    assert would_create_loop(PARENT_OF, 1, 3)


def test_moving_under_a_sibling_or_to_top_level_is_fine():
    assert not would_create_loop(PARENT_OF, 3, 4)
    assert not would_create_loop(PARENT_OF, 2, 4)
    assert not would_create_loop(PARENT_OF, 3, None)


def test_moving_under_own_parent_or_ancestor_is_fine():
    assert not would_create_loop(PARENT_OF, 3, 2)
    assert not would_create_loop(PARENT_OF, 3, 1)


def test_finishes_even_if_the_data_already_has_a_loop():
    broken = {1: 2, 2: 1, 3: None}

    assert not would_create_loop(broken, 3, 1)
