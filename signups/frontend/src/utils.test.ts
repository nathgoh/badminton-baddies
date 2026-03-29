import { describe, it, expect } from 'vitest'
import { formatTime } from './utils'

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
