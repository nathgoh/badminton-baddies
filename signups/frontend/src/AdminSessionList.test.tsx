import { readFileSync } from 'node:fs'

import { describe, expect, it } from 'vitest'

describe('AdminSessionList structure hooks', () => {
  it('includes the mobile-first admin structure class hooks in the page source', () => {
    const source = readFileSync(new URL('./pages/AdminSessionList.tsx', import.meta.url), 'utf8')

    expect(source).toContain('admin-sessions-page')
    expect(source).toContain('admin-session-card')
    expect(source).toContain('admin-session-form')
    expect(source).toContain('admin-court-block')
  })
})
