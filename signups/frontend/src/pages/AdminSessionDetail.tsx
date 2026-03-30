import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import CostCalculator from '../components/CostCalculator'
import RosterManager from '../components/RosterManager'
import { calculateCosts, getAdminSession, updateSession } from '../api/client'
import { formatDisplayDate } from '../utils'
import type { AdminSessionResponse } from '../types'

export default function AdminSessionDetail() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<AdminSessionResponse | null>(null)
  const [toggling, setToggling] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [result, setResult] = useState<{ base_amount: number } | null>(null)

  async function load() {
    if (!id) {
      return
    }
    setData(await getAdminSession(id))
  }

  useEffect(() => {
    void load()
  }, [id])

  async function handleToggleActive() {
    if (!data) return
    setToggling(true)
    try {
      await updateSession(data.session.id, { is_active: !data.session.is_active })
      void load()
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    } finally {
      setToggling(false)
    }
  }

  async function handleCalculate() {
    if (!data) return
    setCalculating(true)
    try {
      const response = await calculateCosts(data.session.id)
      setResult(response)
      void load()
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    } finally {
      setCalculating(false)
    }
  }

  if (!data) {
    return (
      <div className="admin-shell admin-session-detail-page">
        <div className="admin-card admin-session-detail-loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="admin-shell admin-session-detail-page">
      <section className="admin-page-header">
        <Link className="admin-back-link" to="/admin">
          ← Back to sessions
        </Link>
        <div className="admin-card-label">Session detail</div>
        <h1 className="admin-card-title">{data.session.name}</h1>
        <p className="admin-session-detail-summary">
          {formatDisplayDate(data.session.date)} · {data.confirmed_count} confirmed · {data.waitlist_count}{' '}
          waitlisted
        </p>
      </section>

      <div className="admin-session-detail-stack">
        <section className="admin-card admin-session-detail-hero">
          <div className="admin-session-detail-hero-top">
            <div>
              <div className="admin-card-label">Overview</div>
              <h2 className="admin-session-detail-hero-title">Session controls</h2>
            </div>
            <span className={`admin-pill${data.session.is_active ? ' is-active' : ' is-draft'}`}>
              {data.session.is_active ? 'Active' : 'Draft'}
            </span>
          </div>

          <div className="admin-session-detail-meta">
            <div className="admin-session-detail-meta-item">
              <span className="admin-meta-label">Date</span>
              <strong>{formatDisplayDate(data.session.date)}</strong>
            </div>
            <div className="admin-session-detail-meta-item">
              <span className="admin-meta-label">Capacity</span>
              <strong>{data.total_capacity} spots</strong>
            </div>
            <div className="admin-session-detail-meta-item">
              <span className="admin-meta-label">Confirmed</span>
              <strong>{data.confirmed_count}</strong>
            </div>
            <div className="admin-session-detail-meta-item">
              <span className="admin-meta-label">Waitlist</span>
              <strong>{data.waitlist_count}</strong>
            </div>
            <div className="admin-session-detail-meta-item">
              <span className="admin-meta-label">Cancel window</span>
              <strong>{data.session.cancel_window_hours} hours</strong>
            </div>
          </div>

          <div className="admin-session-controls-costs">
            <div className="admin-card-label">Cost split</div>
            <div className="admin-session-controls-cost-grid">
              <div className="admin-session-controls-cost-row">
                <span>Total court cost</span>
                <strong>${data.total_cost.toFixed(2)}</strong>
              </div>
              {result ? (
                <div className="admin-session-controls-cost-row admin-session-controls-cost-row-emphasis">
                  <span>Base per player</span>
                  <strong>${result.base_amount.toFixed(2)}</strong>
                </div>
              ) : null}
            </div>
            <div className="admin-session-controls-actions">
              <button type="button" className="admin-session-toggle-button" onClick={() => void handleToggleActive()} disabled={toggling}>
                {toggling ? 'Saving...' : data.session.is_active ? 'Close session' : 'Open session'}
              </button>
              <button type="button" className="admin-session-calculate-button" onClick={() => void handleCalculate()} disabled={calculating}>
                {calculating ? 'Calculating...' : 'Calculate & assign costs'}
              </button>
            </div>
          </div>
        </section>

        <CostCalculator data={data} onRefresh={() => void load()} />
        <RosterManager signups={data.signups} onRefresh={() => void load()} />
      </div>
    </div>
  )
}
