import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import CostCalculator from '../components/CostCalculator'
import RosterManager from '../components/RosterManager'
import { createCourt, createSession, deleteSession, getAdminSession, listSessions } from '../api/client'
import { useAdminAuth } from '../auth/useAdminAuth'
import { nextExpandedId, isPastSession } from '../utils'
import type { AdminSessionResponse, Session } from '../types'

interface NewCourtForm {
  name: string
  start_time: string
  end_time: string
  max_players: string
  total_cost: string
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

function formatCancelWindow(hours: number) {
  if (hours % 24 === 0) {
    const days = hours / 24
    return `${days} day${days === 1 ? '' : 's'}`
  }

  return `${hours} hour${hours === 1 ? '' : 's'}`
}

export default function AdminSessionList() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [showForm, setShowForm] = useState(false)
  const [sessionName, setSessionName] = useState('')
  const [sessionDate, setSessionDate] = useState('')
  const [cancelWindow, setCancelWindow] = useState('48')
  const [courts, setCourts] = useState<NewCourtForm[]>([
    { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' },
  ])
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [expandedData, setExpandedData] = useState<AdminSessionResponse | null>(null)
  const { logout, email } = useAdminAuth()
  const navigate = useNavigate()

  async function load() {
    setSessions(await listSessions())
  }

  useEffect(() => {
    void load()
  }, [])

  async function handleRowClick(session: Session) {
    const newId = nextExpandedId(expandedId, session.id)
    if (newId === null) {
      setExpandedId(null)
      setExpandedData(null)
      return
    }

    try {
      const data = await getAdminSession(session.id)
      setExpandedId(session.id)
      setExpandedData(data)
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    }
  }

  async function handleExpandedRefresh() {
    if (!expandedId) return

    try {
      setExpandedData(await getAdminSession(expandedId))
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    }
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    try {
      const session = await createSession({
        name: sessionName,
        date: sessionDate,
        is_active: false,
        cancel_window_hours: parseInt(cancelWindow, 10),
      })

      for (const court of courts) {
        if (!court.name) continue

        await createCourt(session.id, {
          name: court.name,
          start_time: court.start_time,
          end_time: court.end_time,
          max_players: parseInt(court.max_players, 10),
          total_cost: parseFloat(court.total_cost),
        })
      }

      setShowForm(false)
      setSessionName('')
      setSessionDate('')
      setCancelWindow('48')
      setCourts([{ name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' }])
      await load()
    } catch (caughtError) {
      setError(errorMessage(caughtError))
    }
  }

  async function handleDelete(session: Session) {
    if (!confirm(`Delete "${session.name}"? This cannot be undone.`)) return

    await deleteSession(session.id)

    if (expandedId === session.id) {
      setExpandedId(null)
      setExpandedData(null)
    }

    await load()
  }

  function updateCourt(index: number, field: keyof NewCourtForm, value: string) {
    setCourts((current) =>
      current.map((court, courtIndex) =>
        courtIndex === index ? { ...court, [field]: value } : court,
      ),
    )
  }

  const upcomingSessions = sessions.filter((s) => !isPastSession(s.date))
  const pastSessions = sessions.filter((s) => isPastSession(s.date))

  return (
    <div className="admin-sessions-page">
      <section className="admin-sessions-hero">
        <div className="admin-sessions-hero-copy">
          <div className="admin-sessions-eyebrow">Court signup admin</div>
          <h1 className="admin-sessions-title">Sessions</h1>
          <p className="admin-sessions-subtitle">
            Manage session setup, court pricing, and roster changes from one mobile-friendly queue.
          </p>
          <div className="admin-sessions-email">{email}</div>
        </div>

        <div className="admin-sessions-actions">
          <button
            className="admin-sessions-action-button"
            onClick={() => navigate('/admin/players')}
            type="button"
          >
            Players
          </button>
          <button
            className="admin-sessions-action-button"
            onClick={() => {
              logout()
              navigate('/admin/login')
            }}
            type="button"
          >
            Sign out
          </button>
        </div>
      </section>

      <section className="admin-sessions-toolbar">
        <div>
          <div className="admin-sessions-toolbar-label">Admin queue</div>
          <h2 className="admin-sessions-toolbar-title">Upcoming sessions</h2>
        </div>
        <button
          className="admin-sessions-primary-button"
          onClick={() => setShowForm(true)}
          type="button"
        >
          + New session
        </button>
      </section>

      {showForm ? (
        <form className="admin-session-form" onSubmit={handleCreate}>
          <div className="admin-session-form-header">
            <div>
              <div className="admin-session-form-label">New session</div>
              <h3 className="admin-session-form-title">Create a session</h3>
            </div>
            <button
              className="admin-sessions-action-button"
              onClick={() => setShowForm(false)}
              type="button"
            >
              Close
            </button>
          </div>

          {error ? <div className="admin-sessions-inline-error">{error}</div> : null}

          <div className="admin-session-fields">
            <label className="admin-session-field">
              <span>Session name *</span>
              <input
                onChange={(event) => setSessionName(event.target.value)}
                required
                value={sessionName}
              />
            </label>
            <label className="admin-session-field">
              <span>Date *</span>
              <input
                min={new Date().toISOString().slice(0, 10)}
                onChange={(event) => setSessionDate(event.target.value)}
                required
                type="date"
                value={sessionDate}
              />
            </label>
            <label className="admin-session-field">
              <span>Cancel window (hours)</span>
              <input
                onChange={(event) => setCancelWindow(event.target.value)}
                type="number"
                value={cancelWindow}
              />
            </label>
          </div>

          <div className="admin-session-courts-header">
            <div>
              <div className="admin-session-form-label">Courts</div>
              <h4 className="admin-session-courts-title">Court blocks</h4>
            </div>
            <button
              className="admin-sessions-action-button"
              onClick={() =>
                setCourts((current) => [
                  ...current,
                  { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' },
                ])
              }
              type="button"
            >
              + Add court
            </button>
          </div>

          <div className="admin-session-courts">
            {courts.map((court, index) => (
              <div className="admin-court-block" key={index}>
                <div className="admin-court-block-header">
                  <div>
                    <div className="admin-session-form-label">Court {index + 1}</div>
                    <div className="admin-court-block-title">Schedule and capacity</div>
                  </div>
                  <button
                    className="admin-sessions-delete-button"
                    onClick={() => {
                      if (courts.length === 1) {
                        setError('At least one court is required.')
                        return
                      }

                      setError(null)
                      setCourts((current) => current.filter((_, courtIndex) => courtIndex !== index))
                    }}
                    type="button"
                  >
                    Remove
                  </button>
                </div>

                <div className="admin-court-block-fields">
                  <label className="admin-session-field">
                    <span>Court name</span>
                    <input
                      onChange={(event) => updateCourt(index, 'name', event.target.value)}
                      placeholder="Court name"
                      value={court.name}
                    />
                  </label>
                  <label className="admin-session-field">
                    <span>Start time</span>
                    <input
                      onChange={(event) => updateCourt(index, 'start_time', event.target.value)}
                      type="time"
                      value={court.start_time}
                    />
                  </label>
                  <label className="admin-session-field">
                    <span>End time</span>
                    <input
                      onChange={(event) => updateCourt(index, 'end_time', event.target.value)}
                      type="time"
                      value={court.end_time}
                    />
                  </label>
                  <label className="admin-session-field">
                    <span>Max spots</span>
                    <input
                      min="1"
                      onChange={(event) => updateCourt(index, 'max_players', event.target.value)}
                      placeholder="Max spots"
                      type="number"
                      value={court.max_players}
                    />
                  </label>
                  <label className="admin-session-field">
                    <span>Total cost</span>
                    <input
                      onChange={(event) => updateCourt(index, 'total_cost', event.target.value)}
                      placeholder="Cost $"
                      type="number"
                      value={court.total_cost}
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>

          <div className="admin-session-form-actions">
            <button className="admin-sessions-primary-button" type="submit">
              Create session
            </button>
            <button
              className="admin-sessions-action-button"
              onClick={() => setShowForm(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {error && !showForm ? <div className="admin-sessions-inline-error">{error}</div> : null}

      <div className="admin-session-list">
        {upcomingSessions.length === 0 ? (
          <div className="admin-session-empty-state">No sessions yet</div>
        ) : null}

        {upcomingSessions.map((session) => {
          const isExpanded = expandedId === session.id

          return (
            <Fragment key={session.id}>
              <article className={`admin-session-card${isExpanded ? ' is-expanded' : ''}`}>
                <button
                  className="admin-session-card-main"
                  onClick={() => void handleRowClick(session)}
                  type="button"
                >
                  <div className="admin-session-card-top">
                    <span className="admin-session-card-chevron" aria-hidden="true">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                    <span className={`admin-session-card-status${session.is_active ? ' is-active' : ''}`}>
                      {session.is_active ? 'Active' : 'Draft'}
                    </span>
                  </div>

                  <div className="admin-session-card-copy">
                    <div className="admin-session-card-name">{session.name}</div>
                    <div className="admin-session-card-date">{session.date}</div>
                  </div>

                  <div className="admin-session-card-stats">
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Cancel window</span>
                      <strong>{formatCancelWindow(session.cancel_window_hours)}</strong>
                    </div>
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Details</span>
                      <strong>{isExpanded ? 'Open' : 'Closed'}</strong>
                    </div>
                  </div>
                </button>

                <div className="admin-session-card-actions">
                  <Link
                    className="admin-session-card-link"
                    onClick={(event) => event.stopPropagation()}
                    to={`/admin/sessions/${session.id}`}
                  >
                    Open details
                  </Link>
                  <button
                    className="admin-sessions-delete-button"
                    onClick={() => void handleDelete(session)}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </article>

              {isExpanded && expandedData ? (
                <div className="admin-session-expanded">
                  <div className="admin-session-expanded-grid">
                    <CostCalculator data={expandedData} onRefresh={() => void handleExpandedRefresh()} />
                    <RosterManager
                      onRefresh={() => void handleExpandedRefresh()}
                      signups={expandedData.signups}
                    />
                  </div>
                </div>
              ) : null}
            </Fragment>
          )
        })}
      </div>

      <section className="admin-sessions-toolbar">
        <div>
          <div className="admin-sessions-toolbar-label">History</div>
          <h2 className="admin-sessions-toolbar-title">Past sessions</h2>
        </div>
      </section>

      <div className="admin-session-list admin-past-session-list">
        {pastSessions.length === 0 ? (
          <div className="admin-session-empty-state">No past sessions</div>
        ) : null}

        {pastSessions.map((session) => {
          const isExpanded = expandedId === session.id

          return (
            <Fragment key={session.id}>
              <article className={`admin-session-card${isExpanded ? ' is-expanded' : ''}`}>
                <button
                  className="admin-session-card-main"
                  onClick={() => void handleRowClick(session)}
                  type="button"
                >
                  <div className="admin-session-card-top">
                    <span className="admin-session-card-chevron" aria-hidden="true">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                    <span className={`admin-session-card-status${session.is_active ? ' is-active' : ''}`}>
                      {session.is_active ? 'Active' : 'Draft'}
                    </span>
                  </div>

                  <div className="admin-session-card-copy">
                    <div className="admin-session-card-name">{session.name}</div>
                    <div className="admin-session-card-date">{session.date}</div>
                  </div>

                  <div className="admin-session-card-stats">
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Cancel window</span>
                      <strong>{formatCancelWindow(session.cancel_window_hours)}</strong>
                    </div>
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Details</span>
                      <strong>{isExpanded ? 'Open' : 'Closed'}</strong>
                    </div>
                  </div>
                </button>

                <div className="admin-session-card-actions">
                  <Link
                    className="admin-session-card-link"
                    onClick={(event) => event.stopPropagation()}
                    to={`/admin/sessions/${session.id}`}
                  >
                    Open details
                  </Link>
                  <button
                    className="admin-sessions-delete-button"
                    onClick={() => void handleDelete(session)}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </article>

              {isExpanded && expandedData ? (
                <div className="admin-session-expanded">
                  <div className="admin-session-expanded-grid">
                    <CostCalculator data={expandedData} onRefresh={() => void handleExpandedRefresh()} />
                    <RosterManager
                      onRefresh={() => void handleExpandedRefresh()}
                      signups={expandedData.signups}
                    />
                  </div>
                </div>
              ) : null}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}
