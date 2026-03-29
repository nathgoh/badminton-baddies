import { useState } from 'react'

import { adminCancelSignup, promoteFromWaitlist, updateSignupAmount } from '../api/client'
import type { Signup } from '../types'

interface Props {
  signups: Signup[]
  onRefresh: () => void
}

export default function RosterManager({ signups, onRefresh }: Props) {
  const confirmed = signups.filter((signup) => signup.status === 'confirmed')
  const waitlisted = signups.filter((signup) => signup.status === 'waitlist')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editAmount, setEditAmount] = useState('')

  async function handleSaveAmount(signupId: string) {
    await updateSignupAmount(signupId, parseFloat(editAmount))
    setEditingId(null)
    onRefresh()
  }

  async function handlePromote(signupId: string) {
    await promoteFromWaitlist(signupId)
    onRefresh()
  }

  async function handleCancel(signupId: string) {
    if (!window.confirm('Cancel this signup?')) {
      return
    }
    await adminCancelSignup(signupId)
    onRefresh()
  }

  return (
    <div>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        Roster
      </div>
      <div
        style={{
          border: '1px solid #e0e0e0',
          borderRadius: 6,
          overflow: 'hidden',
          marginBottom: 20,
        }}
      >
        <div
          style={{
            background: '#f5f5f5',
            padding: '8px 14px',
            display: 'grid',
            gridTemplateColumns: '1fr 80px 70px 90px',
            gap: 8,
            fontSize: 11,
            fontWeight: 600,
            color: '#666',
            borderBottom: '1px solid #e0e0e0',
          }}
        >
          <span>Player</span>
          <span>Status</span>
          <span>Owes</span>
          <span></span>
        </div>
        {confirmed.map((signup) => (
          <div
            key={signup.id}
            style={{
              padding: '10px 14px',
              display: 'grid',
              gridTemplateColumns: '1fr 80px 70px 90px',
              gap: 8,
              alignItems: 'center',
              borderBottom: '1px solid #f5f5f5',
              fontSize: 12,
            }}
          >
            <div>
              <div style={{ fontWeight: 500 }}>{signup.name}</div>
              <div style={{ fontSize: 11, color: '#999' }}>{signup.email}</div>
            </div>
            <div
              style={{
                background: '#e8f5e9',
                color: '#2e7d32',
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 3,
                textAlign: 'center',
              }}
            >
              confirmed
            </div>
            <div>
              {editingId === signup.id ? (
                <input
                  type="number"
                  step="0.01"
                  value={editAmount}
                  onChange={(event) => setEditAmount(event.target.value)}
                  style={{
                    width: '100%',
                    padding: 4,
                    border: '1px solid #3f51b5',
                    borderRadius: 3,
                    fontSize: 12,
                  }}
                  autoFocus
                />
              ) : (
                <span style={{ color: signup.amount_adjusted ? '#e65100' : '#333', fontWeight: 600 }}>
                  {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '-'}
                  {signup.amount_adjusted ? ' ✎' : ''}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {editingId === signup.id ? (
                <>
                  <button
                    onClick={() => void handleSaveAmount(signup.id)}
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
                    onClick={() => setEditingId(null)}
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
                </>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setEditingId(signup.id)
                      setEditAmount(String(signup.amount_owed ?? ''))
                    }}
                    style={{
                      fontSize: 11,
                      color: '#555',
                      border: '1px solid #e0e0e0',
                      borderRadius: 3,
                      padding: '2px 6px',
                      cursor: 'pointer',
                      background: 'white',
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => void handleCancel(signup.id)}
                    style={{
                      fontSize: 11,
                      color: '#c62828',
                      border: '1px solid #ffcdd2',
                      borderRadius: 3,
                      padding: '2px 6px',
                      cursor: 'pointer',
                      background: 'white',
                    }}
                  >
                    x
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {waitlisted.length > 0 ? (
        <>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: '#e65100',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            Waitlist - {waitlisted.length}
          </div>
          <div style={{ border: '1px solid #ffe0b2', borderRadius: 6, overflow: 'hidden' }}>
            {waitlisted.map((signup) => (
              <div
                key={signup.id}
                style={{
                  padding: '10px 14px',
                  display: 'grid',
                  gridTemplateColumns: '1fr auto auto',
                  gap: 8,
                  alignItems: 'center',
                  borderBottom: '1px solid #fff3e0',
                  fontSize: 12,
                }}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>{signup.name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{signup.email}</div>
                </div>
                <button
                  onClick={() => void handlePromote(signup.id)}
                  style={{
                    fontSize: 11,
                    padding: '4px 8px',
                    background: '#e8f5e9',
                    color: '#2e7d32',
                    border: '1px solid #a5d6a7',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                >
                  Promote
                </button>
                <button
                  onClick={() => void handleCancel(signup.id)}
                  style={{
                    fontSize: 11,
                    color: '#c62828',
                    border: '1px solid #ffcdd2',
                    borderRadius: 3,
                    padding: '2px 6px',
                    cursor: 'pointer',
                    background: 'white',
                  }}
                >
                  x
                </button>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

