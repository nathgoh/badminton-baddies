/** Format a "HH:MM" or "H:MM" time string as "7PM", "10:30AM", etc. */
export function formatTime(time: string): string {
  const [hourStr, minuteStr = '0'] = time.split(':')
  const hour = parseInt(hourStr, 10)
  const minute = parseInt(minuteStr, 10)
  const suffix = hour < 12 ? 'AM' : 'PM'
  const hour12 = hour % 12 === 0 ? 12 : hour % 12
  return minute === 0 ? `${hour12}${suffix}` : `${hour12}:${minuteStr}${suffix}`
}
