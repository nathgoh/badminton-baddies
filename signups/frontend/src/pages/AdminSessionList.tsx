import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { createCourt, createSession, deleteSession, getAdminSession, listSessions } from '../api/client'
import { useAdminAuth } from '../auth/useAdminAuth'
import { isPastSession } from '../utils'
import type { AdminSessionResponse } from '../types'

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

function cancelWindowLabel(date: string, cancelWindowHours: number): string {
  const deadlineMs = new Date(date).getTime() - cancelWindowHours * 60 * 60 * 1000
  const daysLeft = Math.ceil((deadlineMs - Date.now()) / (1000 * 60 * 60 * 24))
  if (daysLeft <= 0) return 'Cancellation closed'
  return `${daysLeft} day${daysLeft === 1 ? '' : 's'} to cancel`
}

const inputClassName =
  'w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200'

export default function AdminSessionList() {
  const [sessions, setSessions] = useState<AdminSessionResponse[]>([])
  const [showForm, setShowForm] = useState(false)
  const [sessionName, setSessionName] = useState('')
  const [sessionDate, setSessionDate] = useState('')
  const [cancelWindow, setCancelWindow] = useState('48')
  const [courts, setCourts] = useState<NewCourtForm[]>([
    { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' },
  ])
  const [error, setError] = useState<string | null>(null)
  const { logout, email } = useAdminAuth()
  const navigate = useNavigate()

  async function load() {
    const list = await listSessions()
    const details = await Promise.all(list.map((s) => getAdminSession(s.id)))
    setSessions(details)
  }

  useEffect(() => {
    void load()
  }, [])

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

  async function handleDelete(data: AdminSessionResponse) {
    if (!confirm(`Delete "${data.session.name}"? This cannot be undone.`)) return

    await deleteSession(data.session.id)
    await load()
  }

  function updateCourt(index: number, field: keyof NewCourtForm, value: string) {
    setCourts((current) =>
      current.map((court, courtIndex) =>
        courtIndex === index ? { ...court, [field]: value } : court,
      ),
    )
  }

  const upcomingSessions = sessions.filter((d) => !isPastSession(d.session.date))
  const pastSessions = sessions.filter((d) => isPastSession(d.session.date))

  function renderCard(data: AdminSessionResponse) {
    const { session } = data
    const confirmedSignups = data.signups.filter((s) => s.status === 'confirmed')
    const amountOwed = confirmedSignups.reduce((sum, s) => {
      if (!s.paid && s.amount_owed !== null) return sum + s.amount_owed
      return sum
    }, 0)
    const allSettled = amountOwed === 0

    return (
      <article
        key={session.id}
        className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/70"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="text-xl font-semibold text-ink-950">{session.name}</div>
            <div className="text-sm text-ink-700">
              {new Date(session.date + 'T00:00:00').toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </div>
            <div className="text-xs font-medium text-ink-500">
              {cancelWindowLabel(session.date, session.cancel_window_hours)}
            </div>
          </div>
          <div
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
              session.is_active
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-amber-100 text-amber-700'
            }`}
          >
            {session.is_active ? 'Active' : 'Draft'}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <div className="rounded-[1.5rem] bg-slate-50 px-4 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-700">
              Signed up
            </div>
            <div className="mt-1 text-base font-semibold text-ink-950">
              {data.confirmed_count}
              <span className="text-sm font-normal text-ink-700"> / {data.total_capacity}</span>
            </div>
          </div>
          <div className="rounded-[1.5rem] bg-slate-50 px-4 py-3">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-700">
              Waitlist
            </div>
            <div className="mt-1 text-base font-semibold text-ink-950">
              {data.waitlist_count}
            </div>
          </div>
          <div className={`rounded-[1.5rem] px-4 py-3 ${allSettled ? 'bg-emerald-50' : 'bg-slate-50'}`}>
            <div className={`text-xs font-semibold uppercase tracking-[0.16em] ${allSettled ? 'text-emerald-700' : 'text-ink-700'}`}>
              Still owed
            </div>
            <div className={`mt-1 text-base font-semibold ${allSettled ? 'text-emerald-700' : 'text-ink-950'}`}>
              {allSettled ? 'All paid' : `$${amountOwed.toFixed(2)}`}
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row">
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-900 transition hover:bg-slate-50"
            to={`/admin/sessions/${session.id}`}
          >
            Open details
          </Link>
          <Button
            onClick={() => void handleDelete(data)}
            type="button"
            variant="danger"
          >
            Delete
          </Button>
        </div>
      </article>
    )
  }

  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <section className="relative overflow-hidden rounded-[2rem] bg-ink-950 px-5 py-6 text-white shadow-soft sm:px-8 sm:py-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.2),_transparent_30%)]" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sand-50">
              Court signup admin
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Sessions</h1>
              <p className="text-sm text-slate-200 sm:text-base">
                Manage session setup, court pricing, and roster changes from one mobile-friendly
                queue.
              </p>
            </div>
            <div className="text-sm font-medium text-slate-200">{email}</div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Button
              className="border-white/20 bg-white/10 text-white hover:bg-white/20 focus-visible:ring-white/30"
              onClick={() => navigate('/admin/players')}
              type="button"
              variant="secondary"
            >
              Players
            </Button>
            <Button
              className="border-white/20 bg-white/10 text-white hover:bg-white/20 focus-visible:ring-white/30"
              onClick={() => {
                logout()
                navigate('/admin/login')
              }}
              type="button"
              variant="secondary"
            >
              Sign out
            </Button>
          </div>
        </div>
      </section>

      <div className="mt-5 space-y-5">
        <Card className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
              Admin queue
            </div>
            <h2 className="text-2xl font-semibold text-ink-950">Upcoming sessions</h2>
            <p className="text-sm text-ink-700">
              View signups, waitlist, and outstanding payments at a glance.
            </p>
          </div>
          <Button onClick={() => setShowForm(true)} type="button">
            + New session
          </Button>
        </Card>

        {showForm ? (
          <Card as="form" className="space-y-5" onSubmit={handleCreate}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
                  New session
                </div>
                <h3 className="text-2xl font-semibold text-ink-950">Create a session</h3>
              </div>
              <Button onClick={() => setShowForm(false)} type="button" variant="secondary">
                Close
              </Button>
            </div>

            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-3">
              <label className="grid gap-2 text-sm font-medium text-ink-900">
                <span>Session name *</span>
                <input
                  className={inputClassName}
                  onChange={(event) => setSessionName(event.target.value)}
                  required
                  value={sessionName}
                />
              </label>
              <label className="grid gap-2 text-sm font-medium text-ink-900">
                <span>Date *</span>
                <input
                  className={inputClassName}
                  min={new Date().toISOString().slice(0, 10)}
                  onChange={(event) => setSessionDate(event.target.value)}
                  required
                  type="date"
                  value={sessionDate}
                />
              </label>
              <label className="grid gap-2 text-sm font-medium text-ink-900">
                <span>Cancel window (hours)</span>
                <input
                  className={inputClassName}
                  onChange={(event) => setCancelWindow(event.target.value)}
                  type="number"
                  value={cancelWindow}
                />
              </label>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
                  Courts
                </div>
                <h4 className="text-xl font-semibold text-ink-950">Court blocks</h4>
              </div>
              <Button
                onClick={() =>
                  setCourts((current) => [
                    ...current,
                    {
                      name: '',
                      start_time: '19:00',
                      end_time: '22:00',
                      max_players: '6',
                      total_cost: '',
                    },
                  ])
                }
                type="button"
                variant="secondary"
              >
                + Add court
              </Button>
            </div>

            <div className="grid gap-4">
              {courts.map((court, index) => (
                <div
                  className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4"
                  key={index}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="space-y-1">
                      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-700">
                        Court {index + 1}
                      </div>
                      <div className="text-lg font-semibold text-ink-950">
                        Schedule and capacity
                      </div>
                    </div>
                    <Button
                      onClick={() => {
                        if (courts.length === 1) {
                          setError('At least one court is required.')
                          return
                        }

                        setError(null)
                        setCourts((current) =>
                          current.filter((_, courtIndex) => courtIndex !== index),
                        )
                      }}
                      type="button"
                      variant="ghost"
                    >
                      Remove
                    </Button>
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Court name</span>
                      <input
                        className={inputClassName}
                        onChange={(event) => updateCourt(index, 'name', event.target.value)}
                        placeholder="Court name"
                        value={court.name}
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Start time</span>
                      <input
                        className={inputClassName}
                        onChange={(event) => updateCourt(index, 'start_time', event.target.value)}
                        type="time"
                        value={court.start_time}
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>End time</span>
                      <input
                        className={inputClassName}
                        onChange={(event) => updateCourt(index, 'end_time', event.target.value)}
                        type="time"
                        value={court.end_time}
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Max spots</span>
                      <input
                        className={inputClassName}
                        min="1"
                        onChange={(event) => updateCourt(index, 'max_players', event.target.value)}
                        placeholder="Max spots"
                        type="number"
                        value={court.max_players}
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Total cost</span>
                      <input
                        className={inputClassName}
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

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="submit">Create session</Button>
              <Button onClick={() => setShowForm(false)} type="button" variant="secondary">
                Cancel
              </Button>
            </div>
          </Card>
        ) : null}

        {error && !showForm ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4">
          {upcomingSessions.length === 0 ? (
            <Card className="text-center text-ink-700">No sessions yet</Card>
          ) : null}

          {upcomingSessions.map(renderCard)}
        </div>

        <Card className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
              History
            </div>
            <h2 className="text-2xl font-semibold text-ink-950">Past sessions</h2>
          </div>
        </Card>

        <div className="grid gap-4">
          {pastSessions.length === 0 ? (
            <Card className="text-center text-ink-700">No past sessions</Card>
          ) : null}

          {pastSessions.map(renderCard)}
        </div>
      </div>
    </div>
  )
}
