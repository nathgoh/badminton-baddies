import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import RosterTab from './components/RosterTab'
import type { Signup } from './types'

function signup(id: string, name: string, status: Signup['status']): Signup {
  return {
    id,
    session_id: 'session-1',
    timestamp: '2026-03-29T00:00:00Z',
    email: `${id}@example.com`,
    name,
    status,
    payment_agreed: true,
    amount_owed: null,
    amount_adjusted: false,
    cancelled_at: null,
    paid: false,
  }
}

describe('RosterTab', () => {
  it('renders confirmed players with summary copy and numbered rows', () => {
    const markup = renderToStaticMarkup(
      <RosterTab
        signups={[
          signup('one', 'lebron james', 'confirmed'),
          signup('two', 'another', 'confirmed'),
          signup('three', 'Johnny', 'waitlist'),
        ]}
      />,
    )

    expect(markup).toContain('public-roster-card-confirmed')
    expect(markup).toContain('Confirmed')
    expect(markup).toContain('2 players in this session')
    expect(markup).toContain('>1<')
    expect(markup).toContain('>2<')
    expect(markup).not.toContain('Full')
  })

  it('renders waitlist rows with row-level W markers only', () => {
    const markup = renderToStaticMarkup(
      <RosterTab signups={[signup('three', 'Johnny', 'waitlist')]} />,
    )

    expect(markup).toContain('public-roster-card-waitlist')
    expect(markup).toContain('Waitlist')
    expect(markup).toContain('1 player waiting')
    expect(markup).toContain('>W1<')
    expect(markup).not.toContain('Full')
  })

  it('hides the waitlist section when there are no waitlisted players', () => {
    const markup = renderToStaticMarkup(
      <RosterTab signups={[signup('one', 'lebron james', 'confirmed')]} />,
    )

    expect(markup).not.toContain('Waitlist')
  })
})
