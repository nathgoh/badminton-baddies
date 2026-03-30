import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import CourtCards from '../components/CourtCards'
import CancelSection from '../components/CancelSection'
import RosterTab from '../components/RosterTab'
import SignupForm from '../components/SignupForm'
import { getPublicSession } from '../api/client'
import type { PublicSessionResponse, Signup } from '../types'

type Tab = 'signup' | 'roster'

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
    return <div style={{ textAlign: 'center', marginTop: 60, color: '#888' }}>{error}</div>
  }
  if (!data) {
    return <div style={{ textAlign: 'center', marginTop: 60 }}>Loading...</div>
  }

  const { session, courts, signups, confirmed_count, waitlist_count, total_capacity } = data
  const totalSignups = confirmed_count + waitlist_count

  return (
    <div className="public-signup-page">
      <div className="public-signup-hero">
        <div className="public-signup-hero-top">
          <div className="public-signup-session-meta">
            <div className="public-signup-session-chip">Thursday Session</div>
            <div className="public-signup-session-name">{session.name}</div>
            <div className="public-signup-session-date">{session.date}</div>
          </div>
          <div className="public-signup-availability-card">
            <div className="public-signup-availability-label">Availability</div>
            <div className="public-signup-availability-value">
              {confirmed_count}/{total_capacity}
            </div>
            <div className="public-signup-availability-caption">spots filled</div>
          </div>
        </div>
      </div>

      <div className="public-signup-tabs" role="tablist" aria-label="Signup page sections">
        {(['signup', 'roster'] as Tab[]).map((currentTab) => (
          <button
            key={currentTab}
            onClick={() => setTab(currentTab)}
            className="public-signup-tab"
            type="button"
            role="tab"
            aria-selected={tab === currentTab}
          >
            {currentTab === 'signup' ? 'Sign Up' : `Roster (${totalSignups})`}
          </button>
        ))}
      </div>

      {tab === 'signup' ? (
        <div className="public-signup-content">
          <CourtCards
            courts={courts}
            confirmedCount={confirmed_count}
            waitlistCount={waitlist_count}
            totalCapacity={total_capacity}
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
          {successSignup ? (
            <div className="public-signup-success">
              {successSignup.status === 'confirmed'
                ? "You're signed up!"
                : "You've been added to the waitlist."}
            </div>
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
        <RosterTab signups={signups} />
      )}
    </div>
  )
}
