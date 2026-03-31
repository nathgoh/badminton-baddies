import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import CourtCards from './components/CourtCards'
import signupFormSource from './components/SignupForm.tsx?raw'
import buttonSource from './components/ui/Button.tsx?raw'
import cardSource from './components/ui/Card.tsx?raw'
import fieldSource from './components/ui/Field.tsx?raw'
import signupPageSource from './pages/SignupPage.tsx?raw'
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

    vi.useRealTimers()
  })

  it('includes public shell hooks in SignupPage source', () => {
    expect(signupPageSource).toContain('data-testid="public-shell"')
    expect(signupPageSource).toContain('data-testid="public-hero"')
    expect(signupPageSource).toContain('data-testid="public-tab-bar"')
  })

  it('adds minimal public ui primitives and wires SignupForm through them', () => {
    expect(buttonSource).toContain('export default function Button')
    expect(cardSource).toContain('export default function Card')
    expect(fieldSource).toContain('export default function Field')
    expect(signupFormSource).toContain("from './ui/Button'")
    expect(signupFormSource).toContain("from './ui/Card'")
    expect(signupFormSource).toContain("from './ui/Field'")
  })

  it('uses a waitlist-aware success eyebrow in SignupPage source', () => {
    expect(signupPageSource).toContain("{successSignup.status === 'confirmed' ? 'Confirmed' : 'Waitlist'}")
  })

  it('keeps Button and Card primitives visually neutral in source', () => {
    expect(buttonSource).not.toContain('bg-ink-950')
    expect(buttonSource).not.toContain('bg-rose-600')
    expect(cardSource).not.toContain('shadow-soft')
    expect(cardSource).not.toContain('backdrop-blur-sm')
  })
})
