import { useState } from 'react'

import { createCourt, deleteCourt, regenerateToken, updateCourt } from '../api/client'
import Button from './ui/Button'
import Card from './ui/Card'
import { formatTime } from '../utils'
import type { AdminSessionResponse } from '../types'

interface Props {
  data: AdminSessionResponse
  onRefresh: () => void
}

const EMPTY_COURT = { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' }

interface CourtEdit {
  start_time: string
  end_time: string
  max_players: string
  total_cost: string
}

const inputClassName =
  'w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200'

export default function CostCalculator({ data, onRefresh }: Props) {
  const [copying, setCopying] = useState(false)
  const [showAddCourt, setShowAddCourt] = useState(false)
  const [newCourt, setNewCourt] = useState(EMPTY_COURT)
  const [addingCourt, setAddingCourt] = useState(false)
  const [editingCourtId, setEditingCourtId] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<CourtEdit | null>(null)

  const publicUrl = `${window.location.origin}/s/${data.session.access_token}`

  async function handleRegenerate() {
    if (!window.confirm('This will invalidate the current link. Continue?')) {
      return
    }
    await regenerateToken(data.session.id)
    onRefresh()
  }

  function startEditCourt(courtId: string) {
    const court = data.courts.find((c) => c.id === courtId)
    if (!court) return
    setEditingCourtId(courtId)
    setEditValues({
      start_time: court.start_time,
      end_time: court.end_time,
      max_players: String(court.max_players),
      total_cost: String(court.total_cost),
    })
  }

  async function handleSaveCourt(event: React.FormEvent) {
    event.preventDefault()
    if (!editingCourtId || !editValues) return
    await updateCourt(editingCourtId, {
      start_time: editValues.start_time,
      end_time: editValues.end_time,
      max_players: parseInt(editValues.max_players, 10),
      total_cost: parseFloat(editValues.total_cost),
    })
    setEditingCourtId(null)
    setEditValues(null)
    onRefresh()
  }

  async function handleDeleteCourt(courtId: string) {
    if (!window.confirm('Remove this court?')) return
    await deleteCourt(courtId)
    onRefresh()
  }

  async function handleAddCourt(event: React.FormEvent) {
    event.preventDefault()
    setAddingCourt(true)
    try {
      await createCourt(data.session.id, {
        name: newCourt.name,
        start_time: newCourt.start_time,
        end_time: newCourt.end_time,
        max_players: parseInt(newCourt.max_players, 10),
        total_cost: parseFloat(newCourt.total_cost),
      })
      setNewCourt(EMPTY_COURT)
      setShowAddCourt(false)
      onRefresh()
    } finally {
      setAddingCourt(false)
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(publicUrl)
    setCopying(true)
    window.setTimeout(() => setCopying(false), 1500)
  }

  return (
    <div className="grid gap-4">
      <Card className="space-y-5">
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">Courts</div>
          <div className="text-2xl font-semibold text-ink-950">
            {data.courts.length} court{data.courts.length === 1 ? '' : 's'} configured
          </div>
        </div>
        <div className="space-y-3" data-testid="court-list">
          {data.courts.map((court) =>
            editingCourtId === court.id && editValues ? (
              <form
                key={court.id}
                className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4"
                data-testid="court-item"
                onSubmit={handleSaveCourt}
              >
                <div className="space-y-4">
                  <div className="space-y-1">
                    <div className="text-lg font-semibold text-ink-950">{court.name}</div>
                    <div className="text-sm text-ink-700">
                      {formatTime(court.start_time)} - {formatTime(court.end_time)} · max{' '}
                      {court.max_players} · ${court.total_cost}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Start time</span>
                      <input
                        className={inputClassName}
                        required
                        type="time"
                        value={editValues.start_time}
                        onChange={(e) =>
                          setEditValues((v) => v && ({ ...v, start_time: e.target.value }))
                        }
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>End time</span>
                      <input
                        className={inputClassName}
                        required
                        type="time"
                        value={editValues.end_time}
                        onChange={(e) =>
                          setEditValues((v) => v && ({ ...v, end_time: e.target.value }))
                        }
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Max players</span>
                      <input
                        className={inputClassName}
                        required
                        type="number"
                        min="1"
                        placeholder="Max players"
                        value={editValues.max_players}
                        onChange={(e) =>
                          setEditValues((v) => v && ({ ...v, max_players: e.target.value }))
                        }
                      />
                    </label>
                    <label className="grid gap-2 text-sm font-medium text-ink-900">
                      <span>Total cost</span>
                      <input
                        className={inputClassName}
                        required
                        type="number"
                        step="0.01"
                        placeholder="Cost $"
                        value={editValues.total_cost}
                        onChange={(e) =>
                          setEditValues((v) => v && ({ ...v, total_cost: e.target.value }))
                        }
                      />
                    </label>
                  </div>

                  <div className="flex gap-3">
                    <Button type="submit" variant="secondary">Save</Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => { setEditingCourtId(null); setEditValues(null) }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </form>
            ) : (
              <article
                key={court.id}
                className="rounded-[1.5rem] border border-slate-200 bg-slate-50/70 p-4"
                data-testid="court-item"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-1">
                    <div className="text-lg font-semibold text-ink-950">{court.name}</div>
                    <div className="text-sm text-ink-700">
                      {formatTime(court.start_time)} - {formatTime(court.end_time)} · max{' '}
                      {court.max_players} · ${court.total_cost}
                    </div>
                  </div>
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <Button type="button" variant="secondary" onClick={() => startEditCourt(court.id)}>
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => void handleDeleteCourt(court.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              </article>
            ),
          )}
        </div>

        {showAddCourt ? (
          <form
            className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/80 p-4"
            data-testid="court-item"
            onSubmit={handleAddCourt}
          >
            <div className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <div className="text-lg font-semibold text-ink-950">Add court</div>
                  <div className="text-sm text-ink-700">
                    Create a new court entry for this session.
                  </div>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button type="submit" disabled={addingCourt}>
                    {addingCourt ? 'Adding...' : 'Add'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setShowAddCourt(false)
                      setNewCourt(EMPTY_COURT)
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <label className="grid gap-2 text-sm font-medium text-ink-900">
                  <span>Court name</span>
                  <input
                    className={inputClassName}
                    required
                    placeholder="Court name"
                    value={newCourt.name}
                    onChange={(e) => setNewCourt((c) => ({ ...c, name: e.target.value }))}
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-ink-900">
                  <span>Start time</span>
                  <input
                    className={inputClassName}
                    required
                    type="time"
                    value={newCourt.start_time}
                    onChange={(e) => setNewCourt((c) => ({ ...c, start_time: e.target.value }))}
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-ink-900">
                  <span>End time</span>
                  <input
                    className={inputClassName}
                    required
                    type="time"
                    value={newCourt.end_time}
                    onChange={(e) => setNewCourt((c) => ({ ...c, end_time: e.target.value }))}
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-ink-900">
                  <span>Max players</span>
                  <input
                    className={inputClassName}
                    required
                    type="number"
                    min="1"
                    placeholder="Max players"
                    value={newCourt.max_players}
                    onChange={(e) => setNewCourt((c) => ({ ...c, max_players: e.target.value }))}
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-ink-900">
                  <span>Total cost</span>
                  <input
                    className={inputClassName}
                    required
                    type="number"
                    placeholder="Cost $"
                    value={newCourt.total_cost}
                    onChange={(e) => setNewCourt((c) => ({ ...c, total_cost: e.target.value }))}
                  />
                </label>
              </div>
            </div>
          </form>
        ) : (
          <Button type="button" variant="secondary" onClick={() => setShowAddCourt(true)}>
            + Add court
          </Button>
        )}
      </Card>

      <Card className="space-y-5" data-testid="signup-link-card">
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-700">
            Signup link
          </div>
          <div className="text-2xl font-semibold text-ink-950">Public session access</div>
        </div>
        <div className="overflow-hidden rounded-[1.5rem] border border-sand-100 bg-sand-50/80 px-4 py-3 text-sm text-ink-700">
          <div className="break-all font-medium text-ink-950">{publicUrl}</div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button type="button" variant="secondary" onClick={handleCopy}>
            {copying ? 'Copied!' : 'Copy'}
          </Button>
          <Button type="button" variant="danger" onClick={handleRegenerate}>
            Regenerate
          </Button>
        </div>
      </Card>
    </div>
  )
}
