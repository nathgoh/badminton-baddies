import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import CostCalculator from '../components/CostCalculator'
import RosterManager from '../components/RosterManager'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
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
      <div
        data-testid="admin-detail-shell"
        className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8"
      >
        <Card className="mx-auto mt-16 max-w-xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-700">
            Session detail
          </p>
          <p className="mt-3 text-xl font-semibold text-ink-950">Loading...</p>
        </Card>
      </div>
    )
  }

  return (
    <div
      data-testid="admin-detail-shell"
      className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8"
    >
      <div className="space-y-5">
        <Link
          className="inline-flex w-fit items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-ink-900 transition hover:bg-slate-50"
          to="/admin"
        >
          <span aria-hidden="true">←</span>
          Back to sessions
        </Link>

        <section
          data-testid="admin-detail-hero"
          className="relative overflow-hidden rounded-[2rem] bg-ink-950 px-5 py-6 text-white shadow-soft sm:px-8 sm:py-8"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(245,158,11,0.18),_transparent_30%)]" />
          <div className="relative space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 space-y-3">
                <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sand-50">
                  Session detail
                </div>
                <div className="space-y-2">
                  <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                    {data.session.name}
                  </h1>
                </div>
              </div>

              <span
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${
                  data.session.is_active
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-amber-100 text-amber-700'
                }`}
              >
                {data.session.is_active ? 'Active' : 'Draft'}
              </span>
            </div>

            <div className="grid gap-3 grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                  Date
                </div>
                <div className="mt-2 text-lg font-semibold">{formatDisplayDate(data.session.date)}</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                  Signed up
                </div>
                <div className="mt-2 text-lg font-semibold">
                  {data.confirmed_count}
                  <span className="text-sm font-normal text-slate-300"> / {data.total_capacity}</span>
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                  Waitlist
                </div>
                <div className="mt-2 text-lg font-semibold">{data.waitlist_count}</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                  Cancel window
                </div>
                <div className="mt-2 text-lg font-semibold">
                  {data.session.cancel_window_hours} hours
                </div>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
                  Cost split
                </div>
                <div className="mt-3 space-y-3">
                  <div className="flex items-center justify-between gap-3 rounded-[1.25rem] bg-white/90 px-4 py-3 text-sm text-ink-700">
                    <span>Total court cost</span>
                    <strong className="text-base text-ink-950">${data.total_cost.toFixed(2)}</strong>
                  </div>
                  {result ? (
                    <div className="flex items-center justify-between gap-3 rounded-[1.25rem] bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      <span>Base per player</span>
                      <strong className="text-base">${result.base_amount.toFixed(2)}</strong>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Button
                  className="w-full border-white/20 bg-white/10 text-white hover:bg-white/20 focus-visible:ring-white/30"
                  onClick={() => void handleToggleActive()}
                  disabled={toggling}
                  type="button"
                  variant="secondary"
                >
                  {toggling ? 'Saving...' : data.session.is_active ? 'Close session' : 'Open session'}
                </Button>
                <Button
                  className="w-full border-amber-300 bg-amber-400 text-ink-950 hover:bg-amber-300 focus-visible:ring-amber-200"
                  onClick={() => void handleCalculate()}
                  disabled={calculating}
                  type="button"
                >
                  {calculating ? 'Calculating...' : 'Calculate & assign costs'}
                </Button>
              </div>
            </div>
          </div>
        </section>

        <div
          data-testid="admin-detail-grid"
          className="grid gap-4 xl:grid-cols-[minmax(0,0.98fr)_minmax(0,1.02fr)]"
        >
          <CostCalculator data={data} onRefresh={() => void load()} />
          <RosterManager signups={data.signups} onRefresh={() => void load()} />
        </div>
      </div>
    </div>
  )
}
