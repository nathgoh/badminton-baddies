import { describe, expect, it } from 'vitest'
import AdminLoginSource from './pages/AdminLogin.tsx?raw'

describe('AdminLogin structure hooks', () => {
  it('includes the mobile admin login shell hooks in the page source', () => {
    expect(AdminLoginSource).toContain('admin-shell')
    expect(AdminLoginSource).toContain('admin-login-page')
    expect(AdminLoginSource).toContain('admin-login-card')
  })
})
