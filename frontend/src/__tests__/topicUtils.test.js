import { describe, expect, it } from "vitest";

import { countSubtopics, flattenTree, idsInside, indentedTitle } from "../utils/topics.js";

const topic = (id, title, children = []) => ({ id, title, parent_id: null, prerequisite_ids: [], children });

// Python basics → Loops → For loops, Python basics → Functions, and Files
const TREE = [topic(1, "Python basics", [topic(2, "Loops", [topic(3, "For loops")]), topic(4, "Functions")]), topic(5, "Files")];

describe("topic helpers", () => {
  it("flattens the tree in page order with depths", () => {
    expect(flattenTree(TREE).map((t) => [t.title, t.depth])).toEqual([
      ["Python basics", 0],
      ["Loops", 1],
      ["For loops", 2],
      ["Functions", 1],
      ["Files", 0],
    ]);
  });

  it("flattens an empty tree to an empty list", () => {
    expect(flattenTree([])).toEqual([]);
  });

  it("lists a topic and everything inside it", () => {
    expect(idsInside(TREE[0])).toEqual([1, 2, 3, 4]);
    expect(idsInside(TREE[1])).toEqual([5]);
  });

  it("counts subtopics at any depth", () => {
    expect(countSubtopics(TREE[0])).toBe(3);
    expect(countSubtopics(TREE[1])).toBe(0);
  });

  it("indents titles by depth", () => {
    expect(indentedTitle({ title: "For loops", depth: 2 })).toBe("· · For loops");
    expect(indentedTitle({ title: "Files", depth: 0 })).toBe("Files");
  });
});
