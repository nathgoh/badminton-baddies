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
    <div style={{ maxWidth: 640, margin: '0 auto', fontFamily: 'sans-serif' }}>
      <div style={{ background: '#3f51b5', color: 'white', padding: '20px 24px' }}>
        <div style={{ fontSize: 22, fontWeight: 'bold' }}>{session.name}</div>
        <div style={{ fontSize: 13, opacity: 0.85, marginTop: 4 }}>{session.date}</div>
      </div>

      <div style={{ display: 'flex', borderBottom: '2px solid #e0e0e0' }}>
        {(['signup', 'roster'] as Tab[]).map((currentTab) => (
          <button
            key={currentTab}
            onClick={() => setTab(currentTab)}
            style={{
              padding: '10px 20px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontWeight: tab === currentTab ? 600 : 400,
              color: tab === currentTab ? '#3f51b5' : '#888',
              borderBottom: tab === currentTab ? '2px solid #3f51b5' : 'none',
              marginBottom: -2,
            }}
          >
            {currentTab === 'signup' ? 'Sign Up' : `Roster (${totalSignups})`}
          </button>
        ))}
      </div>

      <div style={{ padding: '20px 24px' }}>
        {tab === 'signup' ? (
          <>
            <CourtCards
              courts={courts}
              confirmedCount={confirmed_count}
              waitlistCount={waitlist_count}
              totalCapacity={total_capacity}
            />
            {successSignup ? (
              <div
                style={{
                  padding: 20,
                  textAlign: 'center',
                  color: '#137333',
                  border: '1px solid #a5d6a7',
                  borderRadius: 8,
                  marginBottom: 16,
                }}
              >
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
            <CancelSection
              token={token!}
              onCancelled={() => {
                setSuccessSignup(null)
                void load()
              }}
            />
          </>
        ) : (
          <RosterTab signups={signups} />
        )}
      </div>
    </div>
  )
}

