import { describe, expect, it } from 'vitest'
import AdminSessionDetailSource from './pages/AdminSessionDetail.tsx?raw'

describe('AdminSessionDetail structure hooks', () => {
  it('includes the admin detail shell structure hooks in the page source', () => {
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-shell["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-hero["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-grid["']/)
  })

  it('preserves the session controls and refresh workflow markers', () => {
    expect(AdminSessionDetailSource).toMatch(
      /async function handleToggleActive\(\) \{[\s\S]*await updateSession\([\s\S]*await load\(\)[\s\S]*\}/,
    )
    expect(AdminSessionDetailSource).toContain(`async function handleRefresh() {
    try {
      await load()`)
    expect(AdminSessionDetailSource).toContain('CostCalculator data={data} onRefresh={handleRefresh}')
    expect(AdminSessionDetailSource).toContain('RosterManager signups={data.signups} onRefresh={handleRefresh}')
    expect(AdminSessionDetailSource).toContain('data.current_base_amount')
    expect(AdminSessionDetailSource).toContain('data.unadjusted_confirmed_count')
    expect(AdminSessionDetailSource).toContain('Cost per player')
    expect(AdminSessionDetailSource).toContain('costPerPlayer={data.current_base_amount ?? undefined}')
    expect(AdminSessionDetailSource).toContain('resetSessionCosts')
    expect(AdminSessionDetailSource).toContain('Reset all to even split')
    expect(AdminSessionDetailSource).not.toContain('handleCalculate')
    expect(AdminSessionDetailSource).not.toContain('calculateCosts')
    expect(AdminSessionDetailSource).not.toContain('Calculate & assign costs')
  })

  it('keeps a single conditional status badge expression', () => {
    expect(AdminSessionDetailSource).toContain("data.session.is_active ? 'Active' : 'Draft'")
  })
})
