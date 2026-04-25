// Backend stores datetimes as naive UTC (no timezone designator).
// Without a 'Z' suffix, JS parses them as local time, showing UTC values as-is.
// This helper appends 'Z' when needed so they're correctly treated as UTC,
// letting date-fns display them in the browser's local timezone.
export function parseDate(str) {
  if (!str) return null
  const hasOffset = str.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(str)
  return new Date(hasOffset ? str : str + 'Z')
}
