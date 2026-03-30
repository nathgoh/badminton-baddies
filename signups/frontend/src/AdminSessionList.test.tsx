import { describe, expect, it } from 'vitest'
import AdminSessionListSource from './pages/AdminSessionList.tsx?raw'

describe('AdminSessionList structure hooks', () => {
  it('includes the mobile-first admin structure class hooks in the page source', () => {
    expect(AdminSessionListSource).toContain('admin-sessions-page')
    expect(AdminSessionListSource).toContain('admin-session-card')
    expect(AdminSessionListSource).toContain('admin-session-form')
    expect(AdminSessionListSource).toContain('admin-court-block')
  })

  it('includes past sessions section', () => {
    expect(AdminSessionListSource).toContain('admin-past-session-list')
    expect(AdminSessionListSource).toContain('pastSessions')
    expect(AdminSessionListSource).toContain('upcomingSessions')
  })
})
