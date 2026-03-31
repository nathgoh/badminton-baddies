import { describe, expect, it } from 'vitest'
import AdminPlayersSource from './pages/AdminPlayers.tsx?raw'

describe('AdminPlayers structure hooks', () => {
  it('includes the admin players shell structure hooks in the page source', () => {
    expect(AdminPlayersSource).toMatch(/data-testid\s*=\s*["']admin-players-shell["']/)
    expect(AdminPlayersSource).toMatch(/data-testid\s*=\s*["']admin-player-card["']/)
    expect(AdminPlayersSource).toMatch(/data-testid\s*=\s*["']admin-player-edit["']/)
  })
})
