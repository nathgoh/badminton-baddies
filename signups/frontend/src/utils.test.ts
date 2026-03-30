import { describe, it, expect } from 'vitest'
import { formatCancellationStatus, formatDisplayDate, formatTime, isPastSession, nextExpandedId } from './utils'

describe('formatTime', () => {
  it('formats a whole PM hour without minutes', () => {
    expect(formatTime('19:00')).toBe('7PM')
  })

  it('formats a whole AM hour without minutes', () => {
    expect(formatTime('07:00')).toBe('7AM')
  })

  it('formats noon as 12PM', () => {
    expect(formatTime('12:00')).toBe('12PM')
  })

  it('formats midnight as 12AM', () => {
    expect(formatTime('00:00')).toBe('12AM')
  })

  it('includes minutes when non-zero', () => {
    expect(formatTime('19:30')).toBe('7:30PM')
  })

  it('includes minutes for AM times', () => {
    expect(formatTime('09:15')).toBe('9:15AM')
  })

  it('formats 10PM correctly', () => {
    expect(formatTime('22:00')).toBe('10PM')
  })
})

describe('nextExpandedId', () => {
  it('returns the clicked id when nothing is expanded', () => {
    expect(nextExpandedId(null, 'abc')).toBe('abc')
  })

  it('returns the clicked id when a different session is expanded', () => {
    expect(nextExpandedId('abc', 'xyz')).toBe('xyz')
  })

  it('returns null when clicking the already-expanded session (collapse)', () => {
    expect(nextExpandedId('abc', 'abc')).toBeNull()
  })
})

describe('formatDisplayDate', () => {
  it('formats an ISO date as Month DD, YYYY', () => {
    expect(formatDisplayDate('2026-04-16')).toBe('April 16, 2026')
  })

  it('returns the original value when the date is invalid', () => {
    expect(formatDisplayDate('not-a-date')).toBe('not-a-date')
  })
})

describe('formatCancellationStatus', () => {
  it('returns days and hours before the cancellation cutoff', () => {
    expect(
      formatCancellationStatus('2026-04-16', 48, new Date('2026-04-11T18:00:00Z')),
    ).toBe('Cancellation closes in 2d 6h')
  })

  it('returns remaining time before the cancellation cutoff', () => {
    expect(
      formatCancellationStatus('2026-04-16', 48, new Date('2026-04-13T10:00:00Z')),
    ).toBe('Cancellation closes in 14h')
  })

  it('returns closed when the cancellation cutoff has passed', () => {
    expect(
      formatCancellationStatus('2026-04-16', 48, new Date('2026-04-14T01:00:00Z')),
    ).toBe('Cancellation closed')
  })
})

describe('isPastSession', () => {
  it('returns true when the session date is before today', () => {
    expect(isPastSession('2026-03-28', '2026-03-30')).toBe(true)
  })

  it('returns false when the session date is today', () => {
    expect(isPastSession('2026-03-30', '2026-03-30')).toBe(false)
  })

  it('returns false when the session date is in the future', () => {
    expect(isPastSession('2026-04-05', '2026-03-30')).toBe(false)
  })
})
