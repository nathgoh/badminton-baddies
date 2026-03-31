import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listPlayers, updatePlayer } from '../api/client'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import type { Player } from '../types'

function formatDate(value: string) {
  return value.split('T')[0]
}

function initials(name: string, email: string) {
  const source = name.trim() || email.trim()
  return source.slice(0, 2).toUpperCase()
}

export default function AdminPlayers() {
  const [players, setPlayers] = useState<Player[]>([])
  const [editingEmail, setEditingEmail] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editVenmo, setEditVenmo] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    void listPlayers().then(setPlayers)
  }, [])

  async function handleSave(email: string) {
    await updatePlayer(email, { name: editName, venmo_or_phone: editVenmo })
    setEditingEmail(null)
    setPlayers(await listPlayers())
  }

  return (
    <div
      data-testid="admin-players-shell"
      className="mx-auto min-h-screen max-w-6xl px-4 py-6 sm:px-6 lg:px-8"
    >
      <div className="space-y-5">
        <section className="relative overflow-hidden rounded-[2rem] bg-ink-950 px-5 py-6 text-white shadow-soft sm:px-8 sm:py-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.2),_transparent_30%)]" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl space-y-3">
              <button
                className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-white/15"
                onClick={() => navigate('/admin')}
                type="button"
              >
                <span aria-hidden="true">←</span>
                Back to sessions
              </button>
              <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sand-50">
                Player database
              </div>
              <div className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Players</h1>
                <p className="text-sm text-slate-200 sm:text-base">
                  Mobile-first cards keep the player record, edit state, and metadata visible
                  without a table layout.
                </p>
              </div>
            </div>

            <Card className="max-w-sm border-white/15 bg-white/10 text-white backdrop-blur-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                Records
              </p>
              <div className="mt-3 text-4xl font-semibold">{players.length}</div>
              <p className="mt-2 text-sm text-slate-200">
                player{players.length === 1 ? '' : 's'} currently saved
              </p>
            </Card>
          </div>
        </section>

        {players.length === 0 ? (
          <Card aria-label="Player records" className="text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
              Player records
            </p>
            <p className="mt-3 text-xl font-semibold text-ink-950">No players yet</p>
          </Card>
        ) : (
          <section aria-label="Player records" className="grid gap-4 lg:grid-cols-2">
            {players.map((player) => {
              const isEditing = editingEmail === player.email

              return (
                <article
                  data-testid="admin-player-card"
                  className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/60"
                  key={player.email}
                >
                  {isEditing ? (
                    <div data-testid="admin-player-edit" className="space-y-4">
                      <div className="space-y-2">
                        <div className="inline-flex rounded-full bg-sand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-ink-700">
                          Editing player
                        </div>
                        <div className="break-all text-sm text-ink-700">{player.email}</div>
                      </div>

                      <label className="grid gap-2 text-sm font-medium text-ink-900">
                        <span>Name</span>
                        <input
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                          value={editName}
                          onChange={(event) => setEditName(event.target.value)}
                          placeholder="Name"
                          type="text"
                        />
                      </label>

                      <label className="grid gap-2 text-sm font-medium text-ink-900">
                        <span>Venmo / Phone</span>
                        <input
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                          value={editVenmo}
                          onChange={(event) => setEditVenmo(event.target.value)}
                          placeholder="Venmo / Phone"
                          type="text"
                        />
                      </label>

                      <div className="flex flex-col gap-3 sm:flex-row">
                        <Button
                          className="sm:flex-1"
                          onClick={() => void handleSave(player.email)}
                          type="button"
                        >
                          Save
                        </Button>
                        <Button
                          className="sm:flex-1"
                          onClick={() => setEditingEmail(null)}
                          type="button"
                          variant="secondary"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-700">
                          {initials(player.name, player.email)}
                        </div>
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="text-xl font-semibold text-ink-950">
                            {player.name || '—'}
                          </div>
                          <div className="break-all text-sm text-ink-700">{player.email}</div>
                        </div>
                      </div>

                      <div className="rounded-[1.5rem] border border-sand-100 bg-sand-50/70 px-4 py-3 text-sm text-ink-700">
                        {player.venmo_or_phone || 'No Venmo / phone yet'}
                      </div>

                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="rounded-[1.5rem] bg-slate-50 px-4 py-3 text-sm text-ink-700">
                          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-700">
                            First seen
                          </div>
                          <div className="mt-1 font-medium text-ink-950">
                            {formatDate(player.first_seen)}
                          </div>
                        </div>

                        <Button
                          onClick={() => {
                            setEditingEmail(player.email)
                            setEditName(player.name)
                            setEditVenmo(player.venmo_or_phone)
                          }}
                          type="button"
                          variant="secondary"
                        >
                          Edit
                        </Button>
                      </div>
                    </div>
                  )}
                </article>
              )
            })}
          </section>
        )}
      </div>
    </div>
  )
}
