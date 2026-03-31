import { useState } from 'react'

import { adminCancelSignup, markSignupPaid, promoteFromWaitlist, updateSignupAmount } from '../api/client'
import Button from './ui/Button'
import Card from './ui/Card'
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
    <div className="grid gap-4">
      <Card className="space-y-5">
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Roster</div>
          <div className="text-2xl font-semibold text-ink-950">
            {confirmed.length} confirmed player{confirmed.length === 1 ? '' : 's'}
          </div>
          <p className="text-xs text-ink-500">Tap card to mark paid · Tap amount to edit</p>
        </div>
        <div className="space-y-3" data-testid="roster-list">
          {confirmed.map((signup) => {
            const isEditing = editingId === signup.id

            return (
              <article
                key={signup.id}
                className={`rounded-[1.5rem] border p-4 transition duration-150 hover:scale-[1.01] hover:shadow-md ${
                  signup.paid
                    ? 'border-emerald-200 bg-emerald-50'
                    : 'border-slate-200 bg-slate-50/70'
                }`}
                data-testid="roster-item"
              >
                <button
                  type="button"
                  className="w-full text-left"
                  data-testid="roster-payment-toggle"
                  onClick={() => void handleTogglePaid(signup.id, signup.paid)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className={`text-lg font-semibold ${signup.paid ? 'text-emerald-900' : 'text-ink-950'}`}>
                        {signup.name}
                      </div>
                      <div className={`break-all text-sm ${signup.paid ? 'text-emerald-700' : 'text-ink-700'}`}>
                        {signup.email}
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          value={editAmount}
                          onChange={(event) => setEditAmount(event.target.value)}
                          className="w-full rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 sm:max-w-[140px]"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span
                          role="button"
                          tabIndex={0}
                          className={`cursor-pointer rounded-full px-4 py-2 text-sm font-semibold transition hover:opacity-80 ${
                            signup.amount_adjusted
                              ? 'bg-amber-100 text-amber-800'
                              : signup.paid
                              ? 'bg-emerald-200 text-emerald-900'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                          onClick={(e) => { e.stopPropagation(); startEditingAmount(signup) }}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); startEditingAmount(signup) } }}
                        >
                          {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '—'}
                        </span>
                      )}
                    </div>
                  </div>
                </button>

                <div className="flex flex-col gap-3 pt-3 sm:flex-row">
                  {isEditing ? (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => void handleSaveAmount(signup.id)}
                    >
                      Save
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => void handleCancel(signup.id)}
                  >
                    Cancel signup
                  </Button>
                </div>
              </article>
            )
          })}
        </div>
      </Card>

      {waitlisted.length > 0 ? (
        <Card className="space-y-5 border-amber-200 bg-amber-50/40">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
              Waitlist
            </div>
            <div className="text-2xl font-semibold text-ink-950">
              {waitlisted.length} waiting player{waitlisted.length === 1 ? '' : 's'}
            </div>
          </div>
          <div className="space-y-3">
            {waitlisted.map((signup) => (
              <article
                key={signup.id}
                className="rounded-[1.5rem] border border-amber-200 bg-white/80 p-4"
              >
                <div className="space-y-3">
                  <div className="space-y-1">
                    <div className="text-lg font-semibold text-ink-950">{signup.name}</div>
                    <div className="break-all text-sm text-ink-700">{signup.email}</div>
                  </div>

                  <div className="flex flex-col gap-3 sm:flex-row">
                    <Button type="button" onClick={() => void handlePromote(signup.id)}>
                      Promote
                    </Button>
                    <Button type="button" variant="danger" onClick={() => void handleCancel(signup.id)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  )
}
