// The four kinds of work and their fixed weights (the same as backend/app/scoring.py).
export const CATEGORIES = [
  { key: "quiz", label: "Quiz", weight: 10 },
  { key: "assignment", label: "Assignment", weight: 10 },
  { key: "midterm", label: "Midterm", weight: 30, inClass: true },
  { key: "project", label: "Project", weight: 50 },
];

export function categoryInfo(key) {
  return CATEGORIES.find((c) => c.key === key) ?? { key, label: key, weight: 0 };
}

/** In-class work (a midterm): nothing to upload, the teacher enters the marks. */
export function isInClass(key) {
  return Boolean(categoryInfo(key).inClass);
}

/** 73.0 -> "73%", 62.5 -> "62.5%", null -> "–" */
export function formatPercent(value) {
  if (value === null || value === undefined) return "–";
  return `${Number(value.toFixed(1))}%`;
}
