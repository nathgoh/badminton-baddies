import { useEffect, useRef, useState, type FocusEvent } from 'react'

import { adminCancelSignup, markSignupPaid, promoteFromWaitlist, updateSignupAmount } from '../api/client'
import Button from './ui/Button'
import Card from './ui/Card'
import type { Signup } from '../types'

interface Props {
  signups: Signup[]
  onRefresh: () => void | Promise<void>
  costPerPlayer?: number
}

export default function RosterManager({ signups, onRefresh, costPerPlayer }: Props) {
  const confirmed = signups.filter((signup) => signup.status === 'confirmed')
  const waitlisted = signups.filter((signup) => signup.status === 'waitlist')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editAmount, setEditAmount] = useState('')
  const [editError, setEditError] = useState<string | null>(null)
  const [optimisticPaid, setOptimisticPaid] = useState<Record<string, boolean>>({})
  const [dropdownId, setDropdownId] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputMouseDownRef = useRef(false)

  useEffect(() => {
    if (!dropdownId) return

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownId(null)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [dropdownId])

  async function handleSaveAmount(editedSignup: Signup) {
    const parsedAmount = parseFloat(editAmount)
    const noOtherUnadjustedConfirmedPlayersRemain = confirmed.every(
      (signup) => signup.id === editedSignup.id || signup.amount_adjusted,
    )
    const amountChanged = parsedAmount !== editedSignup.amount_owed

    if (
      amountChanged &&
      noOtherUnadjustedConfirmedPlayersRemain
    ) {
      setEditError('No other unadjusted confirmed players remain to absorb the remaining cost.')
      return
    }

    try {
      setEditError(null)
      await updateSignupAmount(editedSignup.id, parsedAmount)
      setEditingId(null)
      await onRefresh()
    } catch (error) {
      setEditError(error instanceof Error ? error.message : String(error))
    }
  }

  async function handleResetAmount(signupId: string) {
    if (costPerPlayer == null) return
    setDropdownId(null)
    await updateSignupAmount(signupId, costPerPlayer)
    await onRefresh()
  }

  async function handlePromote(signupId: string) {
    await promoteFromWaitlist(signupId)
    await onRefresh()
  }

  async function handleTogglePaid(signupId: string, currentPaid: boolean) {
    if (currentPaid && !window.confirm('Mark this player as unpaid?')) return
    setOptimisticPaid((prev) => ({ ...prev, [signupId]: !currentPaid }))
    await markSignupPaid(signupId, !currentPaid)
    await onRefresh()
  }

  async function handleMarkAll(paid: boolean) {
    const targets = confirmed.filter((signup) => (optimisticPaid[signup.id] ?? signup.paid) !== paid)
    if (targets.length === 0) return

    const message = paid
      ? `Mark all ${targets.length} player${targets.length === 1 ? '' : 's'} as paid?`
      : `Mark all ${targets.length} player${targets.length === 1 ? '' : 's'} as unpaid?`
    if (!window.confirm(message)) return

    setOptimisticPaid(Object.fromEntries(confirmed.map((signup) => [signup.id, paid])))
    await Promise.all(targets.map((signup) => markSignupPaid(signup.id, paid)))
    await onRefresh()
  }

  async function handleCancel(signupId: string) {
    setDropdownId(null)
    if (!window.confirm('Cancel this signup?')) return
    await adminCancelSignup(signupId)
    await onRefresh()
  }

  function startEditingAmount(signup: Signup) {
    if (signup.paid) {
      return
    }
    setEditingId(signup.id)
    setEditAmount(signup.amount_owed != null ? signup.amount_owed.toFixed(2) : '')
    setEditError(null)
  }

  function handleAmountBlur(event: FocusEvent<HTMLInputElement>) {
    const nextTarget = event.relatedTarget
    if (nextTarget instanceof HTMLElement && nextTarget.closest('[data-edit-amount-control="true"]')) {
      return
    }
    setEditingId(null)
    setEditError(null)
  }

  return (
    <div className="grid gap-4">
      <Card className="space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Roster</div>
            <div className="text-2xl font-semibold text-ink-950">
              {confirmed.length} confirmed player{confirmed.length === 1 ? '' : 's'}
            </div>
            <p className="text-xs text-ink-500">Tap card to mark paid · Tap amount to edit</p>
          </div>
          {confirmed.length > 0
            ? (() => {
                const allPaid = confirmed.every((signup) => optimisticPaid[signup.id] ?? signup.paid)
                return (
                  <button
                    type="button"
                    onClick={() => void handleMarkAll(!allPaid)}
                    className={`shrink-0 rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] transition ${
                      allPaid
                        ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        : 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                    }`}
                  >
                    {allPaid ? 'Mark all unpaid' : 'Mark all paid'}
                  </button>
                )
              })()
            : null}
        </div>
        <div className="space-y-3" data-testid="roster-list">
          {confirmed.map((signup) => {
            const isEditing = editingId === signup.id
            const isPaid = optimisticPaid[signup.id] ?? signup.paid
            const isDropdownOpen = dropdownId === signup.id

            return (
              <article
                key={signup.id}
                className={`rounded-[1.5rem] border p-4 transition duration-150 hover:brightness-95 ${
                  isPaid ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50/70'
                }`}
                data-testid="roster-item"
              >
                <button
                  type="button"
                  className="w-full text-left"
                  data-testid="roster-payment-toggle"
                  onMouseDown={(event) => {
                    if (isEditing && !(event.target instanceof HTMLInputElement)) {
                      event.preventDefault()
                    }
                  }}
                  onClick={() => {
                    if (isEditing) {
                      return
                    }
                    if (inputMouseDownRef.current) {
                      inputMouseDownRef.current = false
                      return
                    }
                    void handleTogglePaid(signup.id, isPaid)
                  }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-lg font-semibold ${isPaid ? 'text-emerald-900' : 'text-ink-950'}`}>
                          {signup.name}
                        </span>
                        {isPaid ? (
                          <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-white">
                            Paid
                          </span>
                        ) : null}
                      </div>
                      <div className={`break-all text-sm ${isPaid ? 'text-emerald-700' : 'text-ink-700'}`}>
                        {signup.email}
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          data-edit-amount-control="true"
                          value={editAmount}
                          onChange={(event) => setEditAmount(event.target.value)}
                          className="w-full rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 sm:max-w-[140px]"
                          autoFocus
                          onFocus={(event) => event.target.select()}
                          onMouseDown={() => {
                            inputMouseDownRef.current = true
                          }}
                          onClick={(event) => event.stopPropagation()}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                              event.stopPropagation()
                              void handleSaveAmount(signup)
                            }
                          }}
                          onBlur={handleAmountBlur}
                        />
                      ) : (
                        <span
                          role="button"
                          tabIndex={0}
                          data-edit-amount-control="true"
                          className={`rounded-full px-5 py-2.5 text-base font-semibold transition ${
                            isPaid
                              ? 'cursor-default bg-emerald-200 text-emerald-900'
                              : signup.amount_adjusted && signup.amount_owed !== costPerPlayer
                                ? 'cursor-pointer bg-blue-100 text-blue-800 hover:opacity-80'
                                : 'cursor-pointer bg-slate-100 text-slate-700 hover:opacity-80'
                          }`}
                          onClick={(event) => {
                            event.stopPropagation()
                            startEditingAmount(signup)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.stopPropagation()
                              startEditingAmount(signup)
                            }
                          }}
                        >
                          {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '—'}
                        </span>
                      )}

                      <div className="relative" ref={isDropdownOpen ? dropdownRef : undefined}>
                        <button
                          type="button"
                          aria-label="More options"
                          disabled={isEditing}
                          className="rounded-full p-2 text-lg text-slate-400 transition hover:bg-slate-200 hover:text-slate-600"
                          onClick={(event) => {
                            event.stopPropagation()
                            setDropdownId(isDropdownOpen ? null : signup.id)
                          }}
                        >
                          ⚙
                        </button>

                        {isDropdownOpen ? (
                          <div className="absolute right-0 top-full z-10 mt-1 w-52 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
                            {costPerPlayer != null ? (
                              <button
                                type="button"
                                className="w-full px-4 py-3 text-left text-sm text-ink-900 transition hover:bg-slate-50"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  void handleResetAmount(signup.id)
                                }}
                              >
                                Reset to ${costPerPlayer.toFixed(2)} / player
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="w-full px-4 py-3 text-left text-sm font-medium text-rose-600 transition hover:bg-rose-50"
                              onClick={(event) => {
                                event.stopPropagation()
                                void handleCancel(signup.id)
                              }}
                            >
                              Cancel signup
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </button>

                {isEditing ? (
                  <div className="pt-3">
                    <Button
                      type="button"
                      data-edit-amount-control="true"
                      className="w-full sm:w-auto"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => void handleSaveAmount(signup)}
                    >
                      Save
                    </Button>
                    {editError ? (
                      <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        {editError}
                      </div>
                    ) : null}
                  </div>
                ) : null}
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
            {waitlisted.map((signup) => {
              const isDropdownOpen = dropdownId === signup.id

              return (
                <article
                  key={signup.id}
                  className="rounded-[1.5rem] border border-amber-200 bg-white/80 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="text-lg font-semibold text-ink-950">{signup.name}</div>
                      <div className="break-all text-sm text-ink-700">{signup.email}</div>
                    </div>

                    <div className="relative shrink-0" ref={isDropdownOpen ? dropdownRef : undefined}>
                      <button
                        type="button"
                        aria-label="More options"
                        className="rounded-full p-2 text-lg text-slate-400 transition hover:bg-amber-100 hover:text-slate-600"
                        onClick={() => setDropdownId(isDropdownOpen ? null : signup.id)}
                      >
                        ⚙
                      </button>

                      {isDropdownOpen ? (
                        <div className="absolute right-0 top-full z-10 mt-1 w-52 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
                          <button
                            type="button"
                            className="w-full px-4 py-3 text-left text-sm text-ink-900 transition hover:bg-slate-50"
                            onClick={() => {
                              setDropdownId(null)
                              void handlePromote(signup.id)
                            }}
                          >
                            Promote to confirmed
                          </button>
                          <button
                            type="button"
                            className="w-full px-4 py-3 text-left text-sm font-medium text-rose-600 transition hover:bg-rose-50"
                            onClick={(event) => {
                              event.stopPropagation()
                              void handleCancel(signup.id)
                            }}
                          >
                            Cancel signup
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </Card>
      ) : null}
    </div>
  )
}
