import { describe, expect, it } from 'vitest'
import AdminSessionDetailSource from './pages/AdminSessionDetail.tsx?raw'

describe('AdminSessionDetail structure hooks', () => {
  it('includes the admin detail shell structure hooks in the page source', () => {
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-shell["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-hero["']/)
    expect(AdminSessionDetailSource).toMatch(/data-testid\s*=\s*["']admin-detail-grid["']/)
  })

  it('preserves the session controls and detail layout coverage', () => {
    expect(AdminSessionDetailSource).toContain('admin-shell')
    expect(AdminSessionDetailSource).toContain('admin-page-header')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-hero')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-stack')
    expect(AdminSessionDetailSource).not.toContain('admin-session-detail-grid')
    expect(AdminSessionDetailSource).toContain('handleToggleActive')
    expect(AdminSessionDetailSource).toContain('handleCalculate')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-costs')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-actions')
  })

  it('renders status badge only once', () => {
    const matches = AdminSessionDetailSource.match(/admin-pill/g)
    expect(matches?.length).toBe(1)
  })
})
