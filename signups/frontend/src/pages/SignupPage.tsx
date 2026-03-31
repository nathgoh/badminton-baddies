import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import CourtCards from '../components/CourtCards'
import CancelSection from '../components/CancelSection'
import RosterTab from '../components/RosterTab'
import SignupForm from '../components/SignupForm'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { getPublicSession } from '../api/client'
import { formatDisplayDate } from '../utils'
import type { PublicSessionResponse, Signup } from '../types'

type Tab = 'signup' | 'roster'

function sessionChipLabel(sessionName: string, sessionDate: string) {
  const [year, month, day] = sessionDate.split('-').map(Number)

  if ([year, month, day].every(Number.isInteger)) {
    const weekday = new Intl.DateTimeFormat(undefined, {
      weekday: 'long',
      timeZone: 'UTC',
    }).format(new Date(Date.UTC(year, month - 1, day)))

    return `${weekday} Session`
  }

  return sessionName || 'Session'
}

export default function SignupPage() {
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<PublicSessionResponse | null>(null)
  const [tab, setTab] = useState<Tab>('signup')
  const [error, setError] = useState<string | null>(null)
  const [successSignup, setSuccessSignup] = useState<Signup | null>(null)
  const [showCancelSection, setShowCancelSection] = useState(false)

  async function load() {
    if (!token) {
      return
    }
    try {
      setData(await getPublicSession(token))
      setError(null)
    } catch {
      setError('Session not found.')
    }
  }

  useEffect(() => {
    void load()
  }, [token])

  if (error) {
    return (
      <div data-testid="public-shell" className="mx-auto min-h-screen max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <Card className="mx-auto mt-16 max-w-xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">Public signup</p>
          <p className="mt-3 text-xl font-semibold text-ink-950">{error}</p>
        </Card>
      </div>
    )
  }
  if (!data) {
    return (
      <div data-testid="public-shell" className="mx-auto min-h-screen max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <Card className="mx-auto mt-16 max-w-xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">Public signup</p>
          <p className="mt-3 text-xl font-semibold text-ink-950">Loading...</p>
        </Card>
      </div>
    )
  }

  const { session, courts, signups, confirmed_count, waitlist_count, total_capacity } = data
  const totalSignups = confirmed_count + waitlist_count
  const chipLabel = sessionChipLabel(session.name, session.date)
  const displayDate = formatDisplayDate(session.date)

  return (
    <div data-testid="public-shell" className="mx-auto min-h-screen max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <section
        data-testid="public-hero"
        className="relative overflow-hidden rounded-[2rem] bg-ink-950 px-5 py-6 text-white shadow-soft sm:px-8 sm:py-8"
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.24),_transparent_30%)]" />
        <div className="relative flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-3">
            <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sand-50">
              {chipLabel}
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{session.name}</h1>
              <p className="text-base text-slate-200 sm:text-lg">{displayDate}</p>
            </div>
          </div>
          <Card className="relative shrink-0 border-sand-100 bg-white/95 text-ink-950">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Availability</p>
            <div className="mt-3 flex items-end gap-2">
              <span className="text-4xl font-semibold">{confirmed_count}</span>
              <span className="pb-1 text-base text-ink-700">/ {total_capacity}</span>
            </div>
            <p className="mt-2 text-sm text-ink-700">spots filled</p>
          </Card>
        </div>
      </section>

      <div
        data-testid="public-tab-bar"
        aria-label="Signup page sections"
        className="mt-4 flex rounded-full border border-white/70 bg-white/80 p-1 shadow-sm backdrop-blur-sm"
      >
        {(['signup', 'roster'] as Tab[]).map((currentTab) => (
          <Button
            key={currentTab}
            onClick={() => setTab(currentTab)}
            variant={tab === currentTab ? 'primary' : 'ghost'}
            className="flex-1"
            type="button"
            aria-pressed={tab === currentTab}
          >
            {currentTab === 'signup' ? 'Sign Up' : `Roster (${totalSignups})`}
          </Button>
        ))}
      </div>

      {tab === 'signup' ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-start">
          <div className="space-y-4">
            <CourtCards
              courts={courts}
              confirmedCount={confirmed_count}
              waitlistCount={waitlist_count}
              totalCapacity={total_capacity}
              sessionDate={session.date}
              cancelWindowHours={session.cancel_window_hours}
            />
            <CancelSection
              token={token!}
              expanded={showCancelSection}
              onToggle={() => setShowCancelSection((value) => !value)}
              onCancelled={() => {
                setSuccessSignup(null)
                setShowCancelSection(false)
                void load()
              }}
            />
          </div>
          {successSignup ? (
            <Card
              className={`space-y-2 ${
                successSignup.status === 'confirmed'
                  ? 'border-emerald-200 bg-emerald-50'
                  : 'border-amber-200 bg-amber-50'
              }`}
            >
              <p
                className={`text-xs font-semibold uppercase tracking-[0.18em] ${
                  successSignup.status === 'confirmed' ? 'text-emerald-700' : 'text-amber-700'
                }`}
              >
                {successSignup.status === 'confirmed' ? 'Confirmed' : 'Waitlist'}
              </p>
              <div className="text-2xl font-semibold text-ink-950">
                {successSignup.status === 'confirmed'
                  ? "You're signed up!"
                  : "You've been added to the waitlist."}
              </div>
              <p className="text-sm text-ink-700">Your roster spot will refresh automatically below.</p>
            </Card>
          ) : (
            <SignupForm
              token={token!}
              isActive={session.is_active}
              isFull={confirmed_count >= total_capacity}
              onSuccess={(signup) => {
                setSuccessSignup(signup)
                void load()
              }}
            />
          )}
        </div>
      ) : (
        <div className="mt-5">
          <RosterTab signups={signups} />
        </div>
      )}
    </div>
  )
}
