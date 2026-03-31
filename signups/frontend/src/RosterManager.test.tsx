import { describe, expect, it } from 'vitest'

import RosterManagerSource from './components/RosterManager.tsx?raw'

describe('RosterManager structure hooks', () => {
  it('includes explicit test ids for roster sections and payment action', () => {
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-list["']/)
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-item["']/)
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-payment-toggle["']/)
    expect(RosterManagerSource).not.toContain('mobileExpandedId')
  })
})
