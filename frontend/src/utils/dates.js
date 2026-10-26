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

/**
 * For <input type="datetime-local">, which works in local time with no timezone:
 * "2026-11-30T18:59:00Z" -> "2026-11-30T23:59" for someone in Pakistan (UTC+5).
 */
export function toLocalInputValue(isoString) {
  const date = new Date(isoString);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

/**
 * The reverse: "2026-11-30T23:59" typed in Pakistan -> "2026-11-30T18:59:00.000Z".
 * The browser knows the viewer's timezone, so the backend always receives UTC.
 */
export function localInputToIso(value) {
  return new Date(value).toISOString();
}
