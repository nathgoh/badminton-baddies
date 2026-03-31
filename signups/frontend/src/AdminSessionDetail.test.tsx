import { describe, expect, it } from 'vitest'
import AdminSessionDetailSource from './pages/AdminSessionDetail.tsx?raw'

describe('AdminSessionDetail structure hooks', () => {
  it('includes the admin detail shell structure hooks in the page source', () => {
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-shell["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-hero["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-grid["']/)
  })

  it('preserves the session controls and refresh workflow markers', () => {
    expect(AdminSessionDetailSource).toContain('handleToggleActive')
    expect(AdminSessionDetailSource).toContain('handleCalculate')
    expect(AdminSessionDetailSource).toContain('CostCalculator')
    expect(AdminSessionDetailSource).toContain('RosterManager')
    expect(AdminSessionDetailSource).toContain('calculateCosts')
    expect(AdminSessionDetailSource).toContain('updateSession')
  })

  it('keeps a single conditional status badge expression', () => {
    expect(AdminSessionDetailSource).toContain("data.session.is_active ? 'Active' : 'Draft'")
  })
})
