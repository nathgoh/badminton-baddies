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
    return <div className="public-signup-form-closed">Signups are closed for this session.</div>
  }

  return (
    <form onSubmit={handleSubmit} className="public-signup-form-card">
      <div className="public-signup-form-title">Sign up</div>
      {error ? <div className="public-signup-inline-error">{error}</div> : null}
      <label className="public-signup-field">
        <span>Email *</span>
        <input
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          onBlur={handleEmailBlur}
        />
      </label>
      <label className="public-signup-field">
        <span>Name *</span>
        <input
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <label className="public-signup-field">
        <span>Venmo or Phone Number *</span>
        <input
          type="text"
          required
          value={venmo}
          onChange={(event) => setVenmo(event.target.value)}
        />
      </label>
      <label className="public-signup-checkbox" htmlFor="payment-agree">
        <input
          id="payment-agree"
          type="checkbox"
          checked={agreed}
          onChange={(event) => setAgreed(event.target.checked)}
        />
        <span>
          I agree to pay if I do not cancel 48 hrs in advance unless I can find
          someone to fill in *
        </span>
      </label>
      <button type="submit" disabled={loading} className="public-signup-submit">
        {loading ? 'Signing up...' : isFull ? 'Join waitlist' : 'Sign up'}
      </button>
    </form>
  )
}
