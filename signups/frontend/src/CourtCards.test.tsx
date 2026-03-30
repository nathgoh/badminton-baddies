import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import CourtCards from './components/CourtCards'
import type { Court } from './types'

function court(id: string): Court {
  return {
    id,
    session_id: 'session-1',
    name: `Court ${id}`,
    start_time: '19:00',
    end_time: '21:00',
    max_players: 6,
    total_cost: 24,
  }
}

describe('CourtCards', () => {
  it('shows remaining spots and cancellation timing when the session is open', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-11T18:00:00Z'))

    const markup = renderToStaticMarkup(
      <CourtCards
        courts={[court('1')]}
        confirmedCount={8}
        waitlistCount={0}
        totalCapacity={10}
        sessionDate="2026-04-16"
        cancelWindowHours={48}
      />,
    )

    expect(markup).toContain('2 spots left before waitlist')
    expect(markup).toContain('Cancellation closes in 2d 6h')
    expect(markup).toContain('>Open<')

    vi.useRealTimers()
  })

  it('shows the full pill without repeating full in the main summary value', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-11T18:00:00Z'))

    const markup = renderToStaticMarkup(
      <CourtCards
        courts={[court('1')]}
        confirmedCount={10}
        waitlistCount={2}
        totalCapacity={10}
        sessionDate="2026-04-16"
        cancelWindowHours={48}
      />,
    )

    expect(markup).toContain('>Full<')
    expect(markup).toContain('Cancellation closes in 2d 6h')
    expect(markup).not.toContain('Full · 2 waitlist')
    expect(markup).not.toContain('public-signup-summary-value')

    vi.useRealTimers()
  })
})
