// The backend always sends times in UTC (ending in "Z"). These helpers show them
// in the viewer's own timezone, which the browser knows automatically.

/** "Sat, 30 Nov 2026, 11:59 pm" in the viewer's local time. */
export function formatDateTime(isoString) {
  if (!isoString) return "";
  return new Date(isoString).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function isPast(isoString) {
  return new Date(isoString).getTime() < Date.now();
}
