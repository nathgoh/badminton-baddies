/** Format a "HH:MM" or "H:MM" time string as "7PM", "10:30AM", etc. */
export function formatTime(time: string): string {
  const [hourStr, minuteStr = '0'] = time.split(':')
  const hour = parseInt(hourStr, 10)
  const minute = parseInt(minuteStr, 10)
  const suffix = hour < 12 ? 'AM' : 'PM'
  const hour12 = hour % 12 === 0 ? 12 : hour % 12
  return minute === 0 ? `${hour12}${suffix}` : `${hour12}:${minuteStr}${suffix}`
}

/** Format an ISO date string as "April 16, 2026" for public display. */
export function formatDisplayDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)

  if (![year, month, day].every(Number.isInteger)) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, day)))
}

/** Format the cancellation cutoff for a session date in UTC. */
export function formatCancellationStatus(
  sessionDate: string,
  cancelWindowHours: number,
  now: Date = new Date(),
): string {
  const [year, month, day] = sessionDate.split('-').map(Number)

  if (![year, month, day].every(Number.isInteger)) {
    return 'Cancellation closed'
  }

  const sessionStart = Date.UTC(year, month - 1, day)
  const cutoff = sessionStart - cancelWindowHours * 60 * 60 * 1000
  const remainingMs = cutoff - now.getTime()

  if (remainingMs <= 0) {
    return 'Cancellation closed'
  }

  const totalHours = Math.floor(remainingMs / (60 * 60 * 1000))
  const days = Math.floor(totalHours / 24)
  const hours = totalHours % 24

  if (days > 0 && hours > 0) {
    return `Cancellation closes in ${days}d ${hours}h`
  }

  if (days > 0) {
    return `Cancellation closes in ${days}d`
  }

  return `Cancellation closes in ${hours}h`
}

/** Returns the next expanded session ID for an accordion toggle.
 *  Clicking the already-expanded session collapses it (returns null).
 *  Clicking a different session expands it (returns its id). */
export function nextExpandedId(currentId: string | null, clickedId: string): string | null {
  return currentId === clickedId ? null : clickedId
}

/** Returns true if the session date (YYYY-MM-DD) is before today's date.
 *  A session on today's date is NOT considered past.
 *  Pass `today` explicitly in tests to avoid depending on the system clock. */
export function isPastSession(date: string, today: string = new Date().toISOString().slice(0, 10)): boolean {
  return date < today
}
