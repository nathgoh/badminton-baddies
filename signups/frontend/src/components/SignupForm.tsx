import { useState } from 'react'

import { lookupPlayer, submitSignup } from '../api/client'
import type { Signup } from '../types'
import Button from './ui/Button'
import Card from './ui/Card'
import Field from './ui/Field'

interface Props {
  token: string
  isActive: boolean
  isFull: boolean
  onSuccess: (signup: Signup) => void
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

const inputClasses =
  'w-full rounded-2xl border border-sand-100 bg-white px-4 py-3 text-sm text-ink-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-2 focus:ring-amber-200'

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
      <Card className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Sign up</p>
        <p className="text-lg font-semibold text-ink-950">Signups are closed for this session.</p>
      </Card>
    )
  }

  return (
    <Card as="form" onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Sign up</p>
        <h2 className="text-2xl font-semibold text-ink-950">
          {isFull ? 'Join the waitlist' : 'Reserve your spot'}
        </h2>
        <p className="text-sm text-ink-700">
          Enter your details and we&apos;ll pull saved info when we recognize your email.
        </p>
      </div>
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
      <Field label="Email *" htmlFor="signup-email">
        <input
          id="signup-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          onBlur={handleEmailBlur}
          className={inputClasses}
        />
      </Field>
      <Field label="Name *" htmlFor="signup-name">
        <input
          id="signup-name"
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className={inputClasses}
        />
      </Field>
      <Field label="Venmo or Phone Number *" htmlFor="signup-venmo">
        <input
          id="signup-venmo"
          type="text"
          required
          value={venmo}
          onChange={(event) => setVenmo(event.target.value)}
          className={inputClasses}
        />
      </Field>
      <label className="flex items-start gap-3 rounded-2xl border border-sand-100 bg-sand-50/70 px-4 py-3 text-sm text-ink-950">
        <input
          type="checkbox"
          tabIndex={0}
          checked={agreed}
          onChange={(event) => setAgreed(event.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-ink-950 focus:ring-amber-500"
        />
        <span>
          I agree to pay if I do not cancel 48 hrs in advance unless I can find someone to fill
          in *
        </span>
      </label>
      <Button type="submit" disabled={loading} fullWidth>
        {loading ? 'Signing up...' : isFull ? 'Join waitlist' : 'Sign up'}
      </Button>
    </Card>
  )
}
