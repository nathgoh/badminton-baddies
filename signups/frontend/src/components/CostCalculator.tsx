import { useState } from 'react'

import { createCourt, deleteCourt, regenerateToken, updateCourt } from '../api/client'
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
    <div className="admin-detail-tools">
      <section className="admin-card admin-courts-card">
        <div className="admin-card-label">Courts</div>
        <div className="admin-court-list">
          {data.courts.map((court) =>
            editingCourtId === court.id && editValues ? (
              <form key={court.id} className="admin-court-item admin-court-item-editing" onSubmit={handleSaveCourt}>
                <div className="admin-court-item-header">
                  <div className="admin-court-item-copy">
                    <div className="admin-court-name">{court.name}</div>
                    <div className="admin-court-meta">
                      {formatTime(court.start_time)} - {formatTime(court.end_time)} · max {court.max_players} · ${court.total_cost}
                    </div>
                  </div>
                  <div className="admin-court-item-actions">
                    <button type="submit" className="admin-secondary-button">
                      Save
                    </button>
                    <button
                      type="button"
                      className="admin-secondary-button"
                      onClick={() => {
                        setEditingCourtId(null)
                        setEditValues(null)
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
                <div className="admin-court-edit-grid">
                  <input
                    required
                    type="time"
                    value={editValues.start_time}
                    onChange={(e) => setEditValues((v) => v && ({ ...v, start_time: e.target.value }))}
                  />
                  <input
                    required
                    type="time"
                    value={editValues.end_time}
                    onChange={(e) => setEditValues((v) => v && ({ ...v, end_time: e.target.value }))}
                  />
                  <input
                    required
                    type="number"
                    min="1"
                    placeholder="Max players"
                    value={editValues.max_players}
                    onChange={(e) => setEditValues((v) => v && ({ ...v, max_players: e.target.value }))}
                  />
                  <input
                    required
                    type="number"
                    step="0.01"
                    placeholder="Cost $"
                    value={editValues.total_cost}
                    onChange={(e) => setEditValues((v) => v && ({ ...v, total_cost: e.target.value }))}
                  />
                </div>
              </form>
            ) : (
              <article key={court.id} className="admin-court-item">
                <div className="admin-court-item-header">
                  <div className="admin-court-item-copy">
                    <div className="admin-court-name">{court.name}</div>
                    <div className="admin-court-meta">
                      {formatTime(court.start_time)} - {formatTime(court.end_time)} · max {court.max_players} · ${court.total_cost}
                    </div>
                  </div>
                  <div className="admin-court-item-actions">
                    <button type="button" className="admin-secondary-button" onClick={() => startEditCourt(court.id)}>
                      Edit
                    </button>
                    <button type="button" className="admin-danger-button" onClick={() => void handleDeleteCourt(court.id)}>
                      Remove
                    </button>
                  </div>
                </div>
              </article>
            ),
          )}
        </div>

        {showAddCourt ? (
          <form className="admin-court-item admin-court-item-add" onSubmit={handleAddCourt}>
            <div className="admin-court-item-header">
              <div className="admin-court-item-copy">
                <div className="admin-court-name">Add court</div>
                <div className="admin-court-meta">Create a new court entry for this session.</div>
              </div>
              <div className="admin-court-item-actions">
                <button type="submit" className="admin-primary-button" disabled={addingCourt}>
                  {addingCourt ? 'Adding...' : 'Add'}
                </button>
                <button
                  type="button"
                  className="admin-secondary-button"
                  onClick={() => {
                    setShowAddCourt(false)
                    setNewCourt(EMPTY_COURT)
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
            <div className="admin-court-edit-grid admin-court-edit-grid-add">
              <input
                required
                placeholder="Court name"
                value={newCourt.name}
                onChange={(e) => setNewCourt((c) => ({ ...c, name: e.target.value }))}
              />
              <input
                required
                type="time"
                value={newCourt.start_time}
                onChange={(e) => setNewCourt((c) => ({ ...c, start_time: e.target.value }))}
              />
              <input
                required
                type="time"
                value={newCourt.end_time}
                onChange={(e) => setNewCourt((c) => ({ ...c, end_time: e.target.value }))}
              />
              <input
                required
                type="number"
                min="1"
                placeholder="Max players"
                value={newCourt.max_players}
                onChange={(e) => setNewCourt((c) => ({ ...c, max_players: e.target.value }))}
              />
              <input
                required
                type="number"
                placeholder="Cost $"
                value={newCourt.total_cost}
                onChange={(e) => setNewCourt((c) => ({ ...c, total_cost: e.target.value }))}
              />
            </div>
          </form>
        ) : (
          <button type="button" className="admin-secondary-button admin-court-add-trigger" onClick={() => setShowAddCourt(true)}>
            + Add court
          </button>
        )}
      </section>

      <section className="admin-card admin-signup-link-card">
        <div className="admin-card-label">Signup link</div>
        <div className="admin-signup-link-value">{publicUrl}</div>
        <div className="admin-signup-link-actions">
          <button type="button" className="admin-secondary-button" onClick={handleCopy}>
            {copying ? 'Copied!' : 'Copy'}
          </button>
          <button type="button" className="admin-danger-button" onClick={handleRegenerate}>
            Regenerate
          </button>
        </div>
      </section>
    </div>
  )
}
