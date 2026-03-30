import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listPlayers, updatePlayer } from '../api/client'
import type { Player } from '../types'
import { useMobile } from '../hooks/useMobile'

export default function AdminPlayers() {
  const [players, setPlayers] = useState<Player[]>([])
  const [editingEmail, setEditingEmail] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editVenmo, setEditVenmo] = useState('')
  const navigate = useNavigate()
  const isMobile = useMobile()

  useEffect(() => {
    void listPlayers().then(setPlayers)
  }, [])

  async function handleSave(email: string) {
    await updatePlayer(email, { name: editName, venmo_or_phone: editVenmo })
    setEditingEmail(null)
    setPlayers(await listPlayers())
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, fontFamily: 'sans-serif' }}>
      <button
        onClick={() => navigate('/admin')}
        style={{
          fontSize: 12,
          color: '#3f51b5',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          marginBottom: 16,
        }}
      >
        ← Back to sessions
      </button>
      <h2 style={{ margin: '0 0 20px' }}>Player Database</h2>
      <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden' }}>
        {!isMobile ? (
          <div
            style={{
              background: '#f5f5f5',
              padding: '10px 16px',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr 1fr 80px',
              gap: 8,
              fontSize: 11,
              fontWeight: 600,
              color: '#666',
              borderBottom: '1px solid #e0e0e0',
            }}
          >
            <span>Email</span>
            <span>Name</span>
            <span>Venmo / Phone</span>
            <span>First seen</span>
            <span></span>
          </div>
        ) : null}
        {players.map((player) => (
          <div
            key={player.email}
            style={
              isMobile
                ? {
                    padding: '12px 14px',
                    borderBottom: '1px solid #f5f5f5',
                    fontSize: 13,
                  }
                : {
                    padding: '10px 16px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr 1fr 80px',
                    gap: 8,
                    alignItems: 'center',
                    borderBottom: '1px solid #f5f5f5',
                    fontSize: 13,
                  }
            }
          >
            {isMobile ? (
              editingEmail === player.email ? (
                <>
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>{player.email}</div>
                  <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    <input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      placeholder="Name"
                      style={{ flex: 1, padding: 6, border: '1px solid #3f51b5', borderRadius: 3, fontSize: 13 }}
                    />
                    <input
                      value={editVenmo}
                      onChange={(event) => setEditVenmo(event.target.value)}
                      placeholder="Venmo / Phone"
                      style={{ flex: 1, padding: 6, border: '1px solid #3f51b5', borderRadius: 3, fontSize: 13 }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      onClick={() => void handleSave(player.email)}
                      style={{ fontSize: 12, padding: '4px 10px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 3, cursor: 'pointer' }}
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingEmail(null)}
                      style={{ fontSize: 12, padding: '4px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{player.name || '—'}</div>
                    <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{player.email}</div>
                    {player.venmo_or_phone ? (
                      <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{player.venmo_or_phone}</div>
                    ) : null}
                    <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>
                      {player.first_seen.split('T')[0]}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setEditingEmail(player.email)
                      setEditName(player.name)
                      setEditVenmo(player.venmo_or_phone)
                    }}
                    style={{ fontSize: 12, padding: '4px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
                  >
                    Edit
                  </button>
                </div>
              )
            ) : (
              <>
                <div style={{ fontSize: 12, color: '#555' }}>{player.email}</div>
                {editingEmail === player.email ? (
                  <>
                    <input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      style={{ padding: 4, border: '1px solid #3f51b5', borderRadius: 3 }}
                    />
                    <input
                      value={editVenmo}
                      onChange={(event) => setEditVenmo(event.target.value)}
                      style={{ padding: 4, border: '1px solid #3f51b5', borderRadius: 3 }}
                    />
                    <div style={{ fontSize: 11, color: '#888' }}>{player.first_seen.split('T')[0]}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => void handleSave(player.email)}
                        style={{
                          fontSize: 11,
                          padding: '2px 6px',
                          background: '#3f51b5',
                          color: 'white',
                          border: 'none',
                          borderRadius: 3,
                          cursor: 'pointer',
                        }}
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingEmail(null)}
                        style={{
                          fontSize: 11,
                          padding: '2px 6px',
                          background: 'white',
                          border: '1px solid #ccc',
                          borderRadius: 3,
                          cursor: 'pointer',
                        }}
                      >
                        x
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div>{player.name}</div>
                    <div>{player.venmo_or_phone}</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{player.first_seen.split('T')[0]}</div>
                    <button
                      onClick={() => {
                        setEditingEmail(player.email)
                        setEditName(player.name)
                        setEditVenmo(player.venmo_or_phone)
                      }}
                      style={{
                        fontSize: 11,
                        padding: '4px 8px',
                        background: 'white',
                        border: '1px solid #ccc',
                        borderRadius: 3,
                        cursor: 'pointer',
                      }}
                    >
                      Edit
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        ))}
        {players.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: '#aaa' }}>No players yet</div>
        ) : null}
      </div>
    </div>
  )
}

