import { describe, expect, it } from 'vitest'
import AdminLoginSource from './pages/AdminLogin.tsx?raw'

describe('AdminLogin structure hooks', () => {
  it('includes the admin login shell structure hooks in the page source', () => {
    expect(AdminLoginSource).toMatch(/data-testid\s*=\s*["']admin-login-shell["']/)
    expect(AdminLoginSource).toMatch(/data-testid\s*=\s*["']admin-login-card["']/)
  })
})
