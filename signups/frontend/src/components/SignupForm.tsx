import { useState } from 'react'

import { lookupPlayer, submitSignup } from '../api/client'
import type { Signup } from '../types'

interface Props {
  token: string
  isActive: boolean
  isFull: boolean
  onSuccess: (signup: Signup) => void
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function SignupForm({ token, isActive, isFull, onSuccess }: Props) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [venmo, setVenmo] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleEmailBlur() {
    if (!email) {
      return
    }
    try {
      const player = await lookupPlayer(token, email)
      setName(player.name)
      setVenmo(player.venmo_or_phone)
    } catch {
      return
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!agreed) {
      setError('Please agree to the payment terms')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const signup = await submitSignup(token, {
        email,
        name,
        venmo_or_phone: venmo,
        payment_agreed: agreed,
      })
      onSuccess(signup)
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    } finally {
      setLoading(false)
    }
  }

  if (!isActive) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#888' }}>
        Signups are closed for this session.
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        border: '1px solid #c5cae9',
        borderRadius: 8,
        padding: 20,
        marginBottom: 16,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 16 }}>Sign up</div>
      {error ? (
        <div style={{ color: '#c62828', marginBottom: 12, fontSize: 13 }}>{error}</div>
      ) : null}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#555' }}>Email *</label>
        <input
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          onBlur={handleEmailBlur}
          style={{
            display: 'block',
            width: '100%',
            padding: 8,
            border: '1px solid #ddd',
            borderRadius: 4,
            marginTop: 4,
          }}
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#555' }}>Name *</label>
        <input
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          style={{
            display: 'block',
            width: '100%',
            padding: 8,
            border: '1px solid #ddd',
            borderRadius: 4,
            marginTop: 4,
          }}
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#555' }}>Venmo or Phone Number *</label>
        <input
          type="text"
          required
          value={venmo}
          onChange={(event) => setVenmo(event.target.value)}
          style={{
            display: 'block',
            width: '100%',
            padding: 8,
            border: '1px solid #ddd',
            borderRadius: 4,
            marginTop: 4,
          }}
        />
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 16 }}>
        <input
          type="checkbox"
          checked={agreed}
          onChange={(event) => setAgreed(event.target.checked)}
          style={{ marginTop: 3 }}
        />
        <label style={{ fontSize: 12, color: '#555' }}>
          I agree to pay if I do not cancel 48 hrs in advance unless I can find
          someone to fill in *
        </label>
      </div>
      <button
        type="submit"
        disabled={loading}
        style={{
          width: '100%',
          padding: 10,
          background: '#3f51b5',
          color: 'white',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
        }}
      >
        {loading ? 'Signing up...' : isFull ? 'Join waitlist' : 'Sign up'}
      </button>
    </form>
  )
}

