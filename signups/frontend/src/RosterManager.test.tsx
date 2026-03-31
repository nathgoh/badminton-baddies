import { describe, expect, it } from 'vitest'

import RosterManagerSource from './components/RosterManager.tsx?raw'

describe('RosterManager structure hooks', () => {
  it('includes explicit test ids for roster sections and payment action', () => {
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-list["']/)
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-item["']/)
    expect(RosterManagerSource).toMatch(/data-testid\s*=\s*["']roster-payment-toggle["']/)
    expect(RosterManagerSource).not.toContain('mobileExpandedId')
  })

  it('keeps the richer roster controls from main while supporting auto refresh', () => {
    expect(RosterManagerSource).toContain('costPerPlayer?: number')
    expect(RosterManagerSource).toContain('const [optimisticPaid, setOptimisticPaid] = useState')
    expect(RosterManagerSource).toContain('const [dropdownId, setDropdownId] = useState')
    expect(RosterManagerSource).toContain('Reset to ${costPerPlayer.toFixed(2)} / player')
    expect(RosterManagerSource).toContain('Mark all paid')
    expect(RosterManagerSource).toContain('Mark all unpaid')
    expect(RosterManagerSource).toContain('Tap card to mark paid')
  })
})
