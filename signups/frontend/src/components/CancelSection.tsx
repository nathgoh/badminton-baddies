import { useId, useState } from 'react'

import { cancelSignup, lookupCancel } from '../api/client'
import type { CancelLookupResponse } from '../types'
import Button from './ui/Button'
import Card from './ui/Card'
import Field from './ui/Field'

interface Props {
  token: string
  expanded: boolean
  onToggle: () => void
  onCancelled: () => void
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

const inputClasses =
  'w-full rounded-2xl border border-sand-100 bg-white px-4 py-3 text-sm text-ink-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-2 focus:ring-amber-200'

export default function CancelSection({ token, expanded, onToggle, onCancelled }: Props) {
  const emailInputId = useId()
  const detailsId = useId()
  const [email, setEmail] = useState('')
  const [lookup, setLookup] = useState<CancelLookupResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleLookup() {
    setError(null)
    setLookup(null)
    try {
      const result = await lookupCancel(token, email)
      setLookup(result)
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    }
  }

  async function handleCancel() {
    if (!lookup) {
      return
    }
    setLoading(true)
    try {
      await cancelSignup(token, lookup.signup.id, email)
      onCancelled()
      setLookup(null)
      setEmail('')
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card data-testid="cancel-card" className="space-y-4">
      <Button
        data-testid="cancel-toggle"
        type="button"
        variant="ghost"
        aria-expanded={expanded}
        aria-controls={detailsId}
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-4 rounded-[1.5rem] border border-sand-100 bg-sand-50/80 px-4 py-3 text-left"
      >
        <span className="text-sm">
          <span className="font-semibold text-ink-950">Already signed up?</span>
          <span className="text-ink-700"> Manage your signup</span>
        </span>
        <span className="rounded-full bg-ink-950 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-white">
          {expanded ? 'Hide' : 'Open'}
        </span>
      </Button>
      {expanded ? (
        <div id={detailsId} className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Field label="Email" htmlFor={emailInputId} className="flex-1">
              <input
                id={emailInputId}
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={inputClasses}
              />
            </Field>
            <Button
              type="button"
              variant="secondary"
              onClick={handleLookup}
              className="sm:mb-0.5"
            >
              Find signup
            </Button>
          </div>
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
          {lookup ? (
            <div className="rounded-[1.5rem] border border-sand-100 bg-sand-50/70 p-4">
              <div className="text-sm text-ink-700">
                Found: <strong>{lookup.signup.name}</strong> - <em>{lookup.signup.status}</em>
              </div>
              {lookup.can_cancel ? (
                <Button
                  type="button"
                  onClick={handleCancel}
                  disabled={loading}
                  variant="danger"
                  className="mt-4 w-full px-5 py-3 text-base sm:w-auto sm:text-sm"
                >
                  {loading ? 'Cancelling...' : 'Cancel my spot'}
                </Button>
              ) : (
                <div className="mt-3 text-sm text-ink-700">{lookup.reason}</div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  )
}
