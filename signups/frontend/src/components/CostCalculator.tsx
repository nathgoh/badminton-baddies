import { useState } from 'react'

import { calculateCosts, regenerateToken, updateSession } from '../api/client'
import { formatTime } from '../utils'
import type { AdminSessionResponse } from '../types'

interface Props {
  data: AdminSessionResponse
  onRefresh: () => void
}

export default function CostCalculator({ data, onRefresh }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ base_amount: number } | null>(null)
  const [copying, setCopying] = useState(false)

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
        {data.courts.map((court) => (
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
                {formatTime(court.start_time)} - {formatTime(court.end_time)} · max {court.max_players} · $
                {court.total_cost}
              </div>
            </div>
          </div>
        ))}
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

