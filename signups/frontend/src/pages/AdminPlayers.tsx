import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listPlayers, updatePlayer } from '../api/client'
import type { Player } from '../types'

function formatDate(value: string) {
  return value.split('T')[0]
}

export default function AdminPlayers() {
  const [players, setPlayers] = useState<Player[]>([])
  const [editingEmail, setEditingEmail] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editVenmo, setEditVenmo] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    void listPlayers().then(setPlayers)
  }, [])

  async function handleSave(email: string) {
    await updatePlayer(email, { name: editName, venmo_or_phone: editVenmo })
    setEditingEmail(null)
    setPlayers(await listPlayers())
  }

  return (
    <div className="admin-shell admin-players-page">
      <section className="admin-page-header">
        <button className="admin-back-link" onClick={() => navigate('/admin')} type="button">
          ← Back to sessions
        </button>
        <div className="admin-card-label">Player database</div>
        <h1 className="admin-card-title">Players</h1>
        <p className="admin-players-summary">
          Mobile-first cards keep the player record, edit state, and metadata visible without a table layout.
        </p>
      </section>

      <section className="admin-card admin-players-list" aria-label="Player records">
        {players.length === 0 ? (
          <div className="admin-players-empty">No players yet</div>
        ) : (
          players.map((player) => {
            const isEditing = editingEmail === player.email

            return (
              <article className="admin-player-card" key={player.email}>
                {isEditing ? (
                  <div className="admin-player-edit">
                    <div className="admin-player-edit-email">{player.email}</div>
                    <label className="admin-player-field">
                      <span>Name</span>
                      <input
                        value={editName}
                        onChange={(event) => setEditName(event.target.value)}
                        placeholder="Name"
                        type="text"
                      />
                    </label>
                    <label className="admin-player-field">
                      <span>Venmo / Phone</span>
                      <input
                        value={editVenmo}
                        onChange={(event) => setEditVenmo(event.target.value)}
                        placeholder="Venmo / Phone"
                        type="text"
                      />
                    </label>
                    <div className="admin-player-edit-actions">
                      <button onClick={() => void handleSave(player.email)} type="button">
                        Save
                      </button>
                      <button onClick={() => setEditingEmail(null)} type="button">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="admin-player-card-main">
                      <div className="admin-player-card-name">{player.name || '—'}</div>
                      <div className="admin-player-card-email">{player.email}</div>
                      <div className="admin-player-card-meta">
                        {player.venmo_or_phone || 'No Venmo / phone yet'}
                      </div>
                    </div>
                    <div className="admin-player-card-side">
                      <div className="admin-player-card-seen">
                        <span className="admin-meta-label">First seen</span>
                        <strong>{formatDate(player.first_seen)}</strong>
                      </div>
                      <button
                        className="admin-player-card-edit-trigger"
                        onClick={() => {
                          setEditingEmail(player.email)
                          setEditName(player.name)
                          setEditVenmo(player.venmo_or_phone)
                        }}
                        type="button"
                      >
                        Edit
                      </button>
                    </div>
                  </>
                )}
              </article>
            )
          })
        )}
      </section>
    </div>
  )
}
