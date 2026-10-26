"""Tree helpers for the course topic tree. Plain Python, no database.

A tree is stored "flat": every item only knows its parent's id (None for a top-level item).
These helpers turn that flat list into nested children, and stop moves that would
put an item inside itself.
"""


def build_tree(items, get_id, get_parent_id):
    """Nest a flat list: returns the top-level items as {"item": ..., "children": [...]}.

    Children keep the order they had in the list. An item whose parent is missing
    from the list is shown at the top level, so nothing is ever lost.
    """
    nodes = {get_id(item): {"item": item, "children": []} for item in items}
    roots = []
    for item in items:
        parent = nodes.get(get_parent_id(item))
        (parent["children"] if parent else roots).append(nodes[get_id(item)])
    return roots


def would_create_loop(parent_of: dict, item_id, new_parent_id) -> bool:
    """True if putting item_id under new_parent_id would make a loop.

    parent_of maps each id to its parent's id (or None). We walk up from the new
    parent towards the top: if we meet item_id on the way, the new parent is the
    item itself or one of its own descendants, and the move must be refused.
    """
    current = new_parent_id
    seen = set()  # guards against a loop already in the data, so this always finishes
    while current is not None and current not in seen:
        if current == item_id:
            return True
        seen.add(current)
        current = parent_of.get(current)
    return False
