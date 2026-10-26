import { isPast } from "../utils/dates.js";

/**
 * Work out a student's status for one assignment. Most important first:
 * graded > submitted > draft > missing (past due, nothing handed in) > assigned.
 */
export function workStatus({ submissionStatus, isLate, grade, dueAt }) {
  if (grade) return { key: "graded", label: "Graded" };
  if (submissionStatus === "submitted") {
    return isLate ? { key: "late", label: "Turned in late" } : { key: "submitted", label: "Turned in" };
  }
  if (isPast(dueAt)) return { key: "missing", label: "Missing" };
  if (submissionStatus === "draft") return { key: "draft", label: "Draft" };
  return { key: "assigned", label: "Assigned" };
}

export default function StatusBadge(props) {
  const status = workStatus(props);
  return <span className={`badge badge-${status.key}`}>{status.label}</span>;
}
