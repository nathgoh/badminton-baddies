import { describe, expect, it } from 'vitest'

import RosterManagerSource from './components/RosterManager.tsx?raw'

describe('RosterManager structure hooks', () => {
  it('includes the flat admin roster class hooks in the source', () => {
    expect(RosterManagerSource).toContain('admin-roster-list')
    expect(RosterManagerSource).toContain('admin-roster-item')
    expect(RosterManagerSource).toContain('admin-roster-payment-toggle')
    expect(RosterManagerSource).not.toContain('mobileExpandedId')
  })
})
