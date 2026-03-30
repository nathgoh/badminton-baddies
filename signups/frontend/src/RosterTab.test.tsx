import { describe, expect, it } from 'vitest'

import rosterTabSource from './components/RosterTab.tsx?raw'

describe('RosterTab', () => {
  it('contains the confirmed and waitlist card hooks in source', () => {
    expect(rosterTabSource).toContain('data-testid="roster-confirmed-card"')
    expect(rosterTabSource).toContain('data-testid="roster-waitlist-card"')
  })
})
