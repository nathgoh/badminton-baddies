import { useState } from 'react'

import { calculateCosts, createCourt, deleteCourt, regenerateToken, updateCourt, updateSession } from '../api/client'
import { formatTime } from '../utils'
import { useMobile } from '../hooks/useMobile'
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
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ base_amount: number } | null>(null)
  const [copying, setCopying] = useState(false)
  const [showAddCourt, setShowAddCourt] = useState(false)
  const [newCourt, setNewCourt] = useState(EMPTY_COURT)
  const [addingCourt, setAddingCourt] = useState(false)
  const isMobile = useMobile()
  const [editingCourtId, setEditingCourtId] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<CourtEdit | null>(null)

  const publicUrl = `${window.location.origin}/s/${data.session.access_token}`

  async function handleCalculate() {
    setLoading(true)
    try {
      const response = await calculateCosts(data.session.id)
      setResult(response)
      onRefresh()
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleActive() {
    await updateSession(data.session.id, { is_active: !data.session.is_active })
    onRefresh()
  }

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
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          onClick={handleToggleActive}
          style={{
            padding: '6px 12px',
            background: data.session.is_active ? '#e8f5e9' : 'white',
            color: data.session.is_active ? '#2e7d32' : '#555',
            border: `1px solid ${data.session.is_active ? '#a5d6a7' : '#ccc'}`,
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          {data.session.is_active ? 'Active - click to close' : 'Closed - click to open'}
        </button>
      </div>

      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        Courts
      </div>
      <div
        style={{
          border: '1px solid #e0e0e0',
          borderRadius: 6,
          overflow: 'hidden',
          marginBottom: 16,
        }}
      >
        {data.courts.map((court) =>
          editingCourtId === court.id && editValues ? (
            <form
              key={court.id}
              onSubmit={handleSaveCourt}
              style={{ padding: '10px 14px', borderBottom: '1px solid #f0f0f0', background: '#f8f9ff' }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>{court.name}</div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 6 }}>
                <input
                  required
                  type="time"
                  value={editValues.start_time}
                  onChange={(e) => setEditValues((v) => v && ({ ...v, start_time: e.target.value }))}
                  style={{ padding: 5, border: '1px solid #c5cae9', borderRadius: 4, fontSize: 12 }}
                />
                <input
                  required
                  type="time"
                  value={editValues.end_time}
                  onChange={(e) => setEditValues((v) => v && ({ ...v, end_time: e.target.value }))}
                  style={{ padding: 5, border: '1px solid #c5cae9', borderRadius: 4, fontSize: 12 }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 8 }}>
                <input
                  required
                  type="number"
                  min="1"
                  placeholder="Max players"
                  value={editValues.max_players}
                  onChange={(e) => setEditValues((v) => v && ({ ...v, max_players: e.target.value }))}
                  style={{ padding: 5, border: '1px solid #c5cae9', borderRadius: 4, fontSize: 12 }}
                />
                <input
                  required
                  type="number"
                  step="0.01"
                  placeholder="Cost $"
                  value={editValues.total_cost}
                  onChange={(e) => setEditValues((v) => v && ({ ...v, total_cost: e.target.value }))}
                  style={{ padding: 5, border: '1px solid #c5cae9', borderRadius: 4, fontSize: 12 }}
                />
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  type="submit"
                  style={{ fontSize: 11, padding: '3px 10px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 3, cursor: 'pointer' }}
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => { setEditingCourtId(null); setEditValues(null) }}
                  style={{ fontSize: 11, padding: '3px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div
              key={court.id}
              style={{
                padding: '12px 14px',
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{court.name}</div>
                <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                  {formatTime(court.start_time)} - {formatTime(court.end_time)} · max {court.max_players} · ${court.total_cost}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  onClick={() => startEditCourt(court.id)}
                  style={{ fontSize: 11, padding: '3px 8px', background: 'white', border: '1px solid #e0e0e0', borderRadius: 3, cursor: 'pointer', color: '#555' }}
                >
                  Edit
                </button>
                <button
                  onClick={() => void handleDeleteCourt(court.id)}
                  style={{ fontSize: 11, padding: '3px 8px', background: 'white', border: '1px solid #ffcdd2', borderRadius: 3, cursor: 'pointer', color: '#c62828' }}
                >
                  x
                </button>
              </div>
            </div>
          )
        )}
      </div>

      {showAddCourt ? (
        <form
          onSubmit={handleAddCourt}
          style={{
            border: '1px solid #c5cae9',
            borderRadius: 6,
            padding: 12,
            marginBottom: 16,
            background: '#f8f9ff',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr 1fr', gap: 6, marginBottom: 6 }}>
            <input
              required
              placeholder="Court name"
              value={newCourt.name}
              onChange={(e) => setNewCourt((c) => ({ ...c, name: e.target.value }))}
              style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
            />
            <input
              required
              type="time"
              value={newCourt.start_time}
              onChange={(e) => setNewCourt((c) => ({ ...c, start_time: e.target.value }))}
              style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
            />
            <input
              required
              type="time"
              value={newCourt.end_time}
              onChange={(e) => setNewCourt((c) => ({ ...c, end_time: e.target.value }))}
              style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 8 }}>
            <input
              required
              type="number"
              min="1"
              placeholder="Max players"
              value={newCourt.max_players}
              onChange={(e) => setNewCourt((c) => ({ ...c, max_players: e.target.value }))}
              style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
            />
            <input
              required
              type="number"
              placeholder="Cost $"
              value={newCourt.total_cost}
              onChange={(e) => setNewCourt((c) => ({ ...c, total_cost: e.target.value }))}
              style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="submit"
              disabled={addingCourt}
              style={{
                padding: '5px 12px',
                background: '#3f51b5',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {addingCourt ? 'Adding...' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => { setShowAddCourt(false); setNewCourt(EMPTY_COURT) }}
              style={{
                padding: '5px 12px',
                background: 'white',
                border: '1px solid #ccc',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          onClick={() => setShowAddCourt(true)}
          style={{
            fontSize: 12,
            padding: '4px 10px',
            background: 'white',
            border: '1px solid #ccc',
            borderRadius: 4,
            cursor: 'pointer',
            marginBottom: 16,
          }}
        >
          + Add court
        </button>
      )}

      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        Cost Split
      </div>
      <div
        style={{
          border: '1px solid #e0e0e0',
          borderRadius: 6,
          padding: 14,
          background: '#fafafa',
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
          <span style={{ color: '#555' }}>Total court cost</span>
          <span style={{ fontWeight: 600 }}>${data.total_cost.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
          <span style={{ color: '#555' }}>Confirmed players</span>
          <span style={{ fontWeight: 600 }}>{data.confirmed_count}</span>
        </div>
        {result ? (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 13,
              fontWeight: 700,
              borderTop: '1px solid #e0e0e0',
              paddingTop: 8,
              marginTop: 6,
            }}
          >
            <span>Base per player</span>
            <span style={{ color: '#3f51b5' }}>${result.base_amount.toFixed(2)}</span>
          </div>
        ) : null}
        <button
          onClick={handleCalculate}
          disabled={loading}
          style={{
            width: '100%',
            marginTop: 12,
            padding: 8,
            background: '#3f51b5',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          {loading ? 'Calculating...' : 'Calculate & assign costs'}
        </button>
      </div>

      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 8,
        }}
      >
        Signup Link
      </div>
      <div style={{ border: '1px solid #e0e0e0', borderRadius: 6, padding: 12, background: '#fafafa' }}>
        <div
          style={{
            fontFamily: 'monospace',
            fontSize: 11,
            color: '#3f51b5',
            background: '#e8eaf6',
            padding: '6px 10px',
            borderRadius: 4,
            marginBottom: 8,
            wordBreak: 'break-all',
          }}
        >
          {publicUrl}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={handleCopy}
            style={{
              flex: 1,
              fontSize: 11,
              padding: 6,
              background: 'white',
              border: '1px solid #ccc',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            {copying ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={handleRegenerate}
            style={{
              flex: 1,
              fontSize: 11,
              padding: 6,
              background: 'white',
              border: '1px solid #ffcdd2',
              borderRadius: 4,
              color: '#c62828',
              cursor: 'pointer',
            }}
          >
            Regenerate
          </button>
        </div>
      </div>
    </div>
  )
}

