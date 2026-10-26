"""Dependency graph helpers. Plain Python, no database, so they can be reused
(topic prerequisites now, course prerequisites later).

A graph is a dict: each node maps to the list of nodes it depends on.
    {"Loops": ["Variables"], "Variables": []}  means  "Loops needs Variables first".
Nodes can be anything hashable (ids, names). A node missing from the dict depends on nothing.
"""

import heapq


class CycleError(Exception):
    """The graph has a loop, so there is no order that puts every dependency first."""

    def __init__(self, cycle: list):
        super().__init__(f"Cycle found: {cycle}")
        self.cycle = cycle  # e.g. ["A", "B", "A"]: A needs B, and B needs A


def find_path(graph: dict, start, goal) -> list | None:
    """A chain of dependencies from start to goal, e.g. [start, x, goal], or None.

    Depth-first search with our own to-do list (a stack) instead of recursion.
    """
    came_from = {start: None}  # also records which nodes we have already visited
    to_visit = [start]
    while to_visit:
        node = to_visit.pop()
        if node == goal:
            path = []
            while node is not None:
                path.append(node)
                node = came_from[node]
            return path[::-1]
        for dependency in graph.get(node, []):
            if dependency not in came_from:
                came_from[dependency] = node
                to_visit.append(dependency)
    return None


def would_create_cycle(graph: dict, node, new_dependency) -> list | None:
    """If "node needs new_dependency" would make a loop, return that loop; otherwise None.

    It makes a loop exactly when new_dependency already needs node (directly or through
    others): node -> new_dependency -> ... -> node.
    """
    if node == new_dependency:
        return [node, node]
    path = find_path(graph, new_dependency, node)
    return [node] + path if path else None


def find_cycle(graph: dict) -> list | None:
    """Any loop in the graph, e.g. ["A", "B", "A"], or None if there is none.

    Depth-first search with three colours: white = not visited yet, grey = on the
    current path, black = finished. Reaching a grey node again means we went in a circle.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {}
    path = []

    def visit(node):
        colour[node] = GREY
        path.append(node)
        for dependency in graph.get(node, []):
            state = colour.get(dependency, WHITE)
            if state == GREY:
                return path[path.index(dependency):] + [dependency]
            if state == WHITE:
                cycle = visit(dependency)
                if cycle:
                    return cycle
        path.pop()
        colour[node] = BLACK
        return None

    for node in graph:
        if colour.get(node, WHITE) == WHITE:
            cycle = visit(node)
            if cycle:
                return cycle
    return None


def dependency_order(nodes: list, graph: dict) -> list:
    """All nodes, ordered so that everything a node needs comes before it.

    This is a topological sort (Kahn's algorithm): repeatedly take a node whose
    dependencies are all placed already. When several are ready, the one listed
    first in nodes goes first, so the result is always the same.
    Raises CycleError if there is a loop.
    """
    position = {node: index for index, node in enumerate(nodes)}
    waiting_on = {node: 0 for node in nodes}  # how many dependencies are not placed yet
    needed_by = {node: [] for node in nodes}  # the reverse direction: who is waiting for me
    for node in nodes:
        for dependency in graph.get(node, []):
            if dependency in position:
                waiting_on[node] += 1
                needed_by[dependency].append(node)

    ready = [position[node] for node in nodes if waiting_on[node] == 0]
    heapq.heapify(ready)  # always gives back the earliest-listed ready node
    order = []
    while ready:
        node = nodes[heapq.heappop(ready)]
        order.append(node)
        for later in needed_by[node]:
            waiting_on[later] -= 1
            if waiting_on[later] == 0:
                heapq.heappush(ready, position[later])

    if len(order) < len(nodes):
        raise CycleError(find_cycle(graph) or [])
    return order
