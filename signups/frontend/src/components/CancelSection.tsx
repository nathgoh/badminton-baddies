import { useId, useState } from 'react'

import { cancelSignup, lookupCancel } from '../api/client'
import type { CancelLookupResponse } from '../types'

interface Props {
  token: string
  expanded: boolean
  onToggle: () => void
  onCancelled: () => void
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

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
    <div className="public-signup-cancel-panel">
      <button
        type="button"
        className="public-signup-cancel-trigger"
        aria-expanded={expanded}
        aria-controls={detailsId}
        onClick={onToggle}
      >
        <span>Already signed up? Cancel your spot</span>
        <span>{expanded ? 'Hide' : 'Open'}</span>
      </button>
      {expanded ? (
        <div id={detailsId} className="public-signup-form">
          <div className="public-signup-field">
            <label htmlFor={emailInputId}>Email</label>
            <input
              id={emailInputId}
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <button type="button" className="public-signup-secondary-button" onClick={handleLookup}>
            Look up my signup
          </button>
          {error ? <div style={{ color: '#c62828', fontSize: 12 }}>{error}</div> : null}
          {lookup ? (
            <div style={{ marginTop: 10, fontSize: 13 }}>
              <div>
                Found: <strong>{lookup.signup.name}</strong> - <em>{lookup.signup.status}</em>
              </div>
              {lookup.can_cancel ? (
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={loading}
                  className="public-signup-danger-button"
                  style={{ marginTop: 8 }}
                >
                  {loading ? 'Cancelling...' : 'Cancel my spot'}
                </button>
              ) : (
                <div style={{ color: '#888', fontSize: 12, marginTop: 6 }}>{lookup.reason}</div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
      <div style={{ fontSize: 11, color: '#aaa', marginTop: 8 }}>
        Cancellation closes 48 hours before the session
      </div>
    </div>
  )
}
