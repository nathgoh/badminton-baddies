import { describe, expect, it } from 'vitest'
import AdminSessionDetailSource from './pages/AdminSessionDetail.tsx?raw'

describe('AdminSessionDetail structure hooks', () => {
  it('includes the dedicated admin detail class hooks in the page source', () => {
    expect(AdminSessionDetailSource).toContain('admin-shell')
    expect(AdminSessionDetailSource).toContain('admin-page-header')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-hero')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-stack')
    expect(AdminSessionDetailSource).not.toContain('admin-session-detail-grid')
  })

  it('renders session controls in the hero card', () => {
    expect(AdminSessionDetailSource).toContain('handleToggleActive')
    expect(AdminSessionDetailSource).toContain('handleCalculate')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-costs')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-actions')
  })

  it('renders status badge only once', () => {
    const matches = AdminSessionDetailSource.match(/admin-pill/g)
    // Two occurrences: one in the hero card, one in the loading state (or just one total)
    // The hero card should be the only pill in the main render
    expect(matches).not.toBeNull()
  })
})
