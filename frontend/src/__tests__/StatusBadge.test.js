import { describe, expect, it } from "vitest";

import { workStatus } from "../components/StatusBadge.jsx";

const FUTURE = "2099-01-01T00:00:00Z";
const PAST = "2000-01-01T00:00:00Z";

describe("workStatus", () => {
  it.each([
    [{ submissionStatus: "none", dueAt: FUTURE }, "Assigned"],
    [{ submissionStatus: "none", dueAt: PAST }, "Missing"],
    [{ submissionStatus: "draft", dueAt: FUTURE }, "Draft"],
    [{ submissionStatus: "draft", dueAt: PAST }, "Missing"], // never marked as done
    [{ submissionStatus: "submitted", isLate: false, dueAt: FUTURE }, "Turned in"],
    [{ submissionStatus: "submitted", isLate: true, dueAt: PAST }, "Turned in late"],
    [{ submissionStatus: "submitted", grade: { score: 18 }, dueAt: PAST }, "Graded"],
    [{ submissionStatus: "none", grade: { score: 0 }, dueAt: PAST }, "Graded"], // missing work given 0
    [{ inClass: true, dueAt: FUTURE }, "In class"], // a midterm before its date
    [{ inClass: true, dueAt: PAST }, "Waiting for marks"], // never "Missing": there's nothing to hand in
    [{ inClass: true, grade: { score: 35 }, dueAt: PAST }, "Graded"],
  ])("%o -> %s", (input, expected) => {
    expect(workStatus(input).label).toBe(expected);
  });
});
