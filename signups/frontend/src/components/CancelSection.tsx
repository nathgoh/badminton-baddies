import { useState } from 'react'

import { cancelSignup, lookupCancel } from '../api/client'
import type { CancelLookupResponse } from '../types'

interface Props {
  token: string
  onCancelled: () => void
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function CancelSection({ token, onCancelled }: Props) {
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
    <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, padding: 16, background: '#fafafa' }}>
      <div style={{ fontWeight: 600, fontSize: 13, color: '#555', marginBottom: 10 }}>
        Already signed up? Cancel your spot
      </div>
      <input
        type="email"
        placeholder="Enter your email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        style={{
          display: 'block',
          width: '100%',
          padding: 8,
          border: '1px solid #ddd',
          borderRadius: 4,
          marginBottom: 8,
        }}
      />
      <button
        onClick={handleLookup}
        style={{
          width: '100%',
          padding: 8,
          background: 'white',
          border: '1px solid #ccc',
          borderRadius: 4,
          cursor: 'pointer',
          marginBottom: 10,
        }}
      >
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
              onClick={handleCancel}
              disabled={loading}
              style={{
                marginTop: 8,
                padding: '6px 14px',
                background: '#c62828',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {loading ? 'Cancelling...' : 'Cancel my spot'}
            </button>
          ) : (
            <div style={{ color: '#888', fontSize: 12, marginTop: 6 }}>{lookup.reason}</div>
          )}
        </div>
      ) : null}
      <div style={{ fontSize: 11, color: '#aaa', marginTop: 8 }}>
        Cancellation closes 48 hours before the session
      </div>
    </div>
  )
}

