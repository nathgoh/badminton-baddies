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

  it('locks the card interactions while an amount input is open', () => {
    expect(RosterManagerSource).toContain('disabled={isEditing}')
    expect(RosterManagerSource).toContain("if (isEditing) {")
  })

  it('does not use delayed blur cleanup that can close the next editor', () => {
    expect(RosterManagerSource).not.toContain('setTimeout(() => setEditingId(null), 150)')
    expect(RosterManagerSource).toContain('relatedTarget')
  })

  it('does not allow amount editing for paid players', () => {
    expect(RosterManagerSource).toContain('if (signup.paid) {')
    expect(RosterManagerSource).toContain('cursor-default')
  })

  it('hard-stops saving when no other unadjusted confirmed players remain', () => {
    expect(RosterManagerSource).toContain('signup.id === editedSignup.id || signup.amount_adjusted')
    expect(RosterManagerSource).toContain('noOtherUnadjustedConfirmedPlayersRemain')
    expect(RosterManagerSource).toContain('No other unadjusted confirmed players remain to absorb the remaining cost.')
    expect(RosterManagerSource).toContain('alert(')
  })
})
