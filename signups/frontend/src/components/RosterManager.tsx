import { useState } from 'react'

import { adminCancelSignup, markSignupPaid, promoteFromWaitlist, updateSignupAmount } from '../api/client'
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

  async function handleTogglePaid(signupId: string, currentPaid: boolean) {
    await markSignupPaid(signupId, !currentPaid)
    onRefresh()
  }

  async function handleCancel(signupId: string) {
    if (!window.confirm('Cancel this signup?')) {
      return
    }
    await adminCancelSignup(signupId)
    onRefresh()
  }

  function startEditingAmount(signup: Signup) {
    setEditingId(signup.id)
    setEditAmount(signup.amount_owed != null ? String(signup.amount_owed) : '')
  }

  return (
    <div className="admin-detail-tools">
      <section className="admin-card admin-roster-card">
        <div className="admin-card-label">Roster</div>
        <div className="admin-roster-list">
          {confirmed.map((signup) => {
            const isEditing = editingId === signup.id

            return (
              <article key={signup.id} className="admin-roster-item">
                <div className="admin-roster-item-header">
                  <div className="admin-roster-item-copy">
                    <div className="admin-roster-name">{signup.name}</div>
                    <div className="admin-roster-email">{signup.email}</div>
                  </div>

                  <div className="admin-roster-item-amount">
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editAmount}
                        onChange={(event) => setEditAmount(event.target.value)}
                        className="admin-roster-amount-input"
                        autoFocus
                      />
                    ) : (
                      <span className={`admin-roster-amount-bubble${signup.amount_adjusted ? ' is-adjusted' : ''}`}>
                        {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '—'}
                      </span>
                    )}
                  </div>
                </div>

                <div className="admin-roster-actions">
                  <button
                    type="button"
                    className="admin-roster-payment-toggle"
                    onClick={() => void handleTogglePaid(signup.id, signup.paid)}
                  >
                    {signup.paid ? 'Paid' : 'Unpaid'}
                  </button>

                  {isEditing ? (
                    <button type="button" className="admin-secondary-button" onClick={() => void handleSaveAmount(signup.id)}>
                      Save
                    </button>
                  ) : (
                    <button type="button" className="admin-secondary-button" onClick={() => startEditingAmount(signup)}>
                      Edit
                    </button>
                  )}

                  <button type="button" className="admin-danger-button" onClick={() => void handleCancel(signup.id)}>
                    Cancel signup
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      {waitlisted.length > 0 ? (
        <section className="admin-card admin-roster-card admin-roster-waitlist-card">
          <div className="admin-card-label">Waitlist</div>
          <div className="admin-waitlist-list">
            {waitlisted.map((signup) => (
              <article key={signup.id} className="admin-waitlist-item">
                <div className="admin-roster-item-header">
                  <div className="admin-roster-item-copy">
                    <div className="admin-roster-name">{signup.name}</div>
                    <div className="admin-roster-email">{signup.email}</div>
                  </div>
                </div>

                <div className="admin-waitlist-actions">
                  <button type="button" className="admin-primary-button" onClick={() => void handlePromote(signup.id)}>
                    Promote
                  </button>
                  <button type="button" className="admin-danger-button" onClick={() => void handleCancel(signup.id)}>
                    Cancel
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
