import { describe, expect, it } from 'vitest'
import AdminPlayersSource from './pages/AdminPlayers.tsx?raw'

describe('AdminPlayers structure hooks', () => {
  it('includes the mobile player card class hooks in the page source', () => {
    expect(AdminPlayersSource).toContain('admin-shell')
    expect(AdminPlayersSource).toContain('admin-players-list')
    expect(AdminPlayersSource).toContain('admin-player-card')
    expect(AdminPlayersSource).toContain('admin-player-edit')
  })
})
