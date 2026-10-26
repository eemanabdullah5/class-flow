// Helpers for the topic tree that comes from GET /api/courses/:id/topics.
// Each topic looks like { id, parent_id, title, prerequisite_ids, children: [...] }.

/**
 * Every topic in the tree as one flat list, in the order they appear on the page,
 * with depth (0 = top level). Used for dropdowns, indented by depth.
 */
export function flattenTree(tree, depth = 0) {
  return tree.flatMap((topic) => [{ ...topic, depth }, ...flattenTree(topic.children, depth + 1)]);
}

/** The ids of a topic and everything inside it. A topic can't be moved into any of these. */
export function idsInside(topic) {
  return [topic.id, ...topic.children.flatMap(idsInside)];
}

/** How many subtopics are inside a topic, at any depth (for "also deletes 3 subtopics"). */
export function countSubtopics(topic) {
  return idsInside(topic).length - 1;
}

/** "Loops" -> "· · Loops" for depth 2, so dropdowns show the tree shape. */
export function indentedTitle(topic) {
  return `${"· ".repeat(topic.depth)}${topic.title}`;
}
