# Session Detail UI Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the admin session detail page by merging the hero card with session controls, removing duplicate status badges, and switching to a single-column stack layout.

**Architecture:** Move session-level actions (toggle active, calculate costs) out of `CostCalculator` and into `AdminSessionDetail`. Merge the hero overview card with those controls. Collapse the two-column grid into a single vertical stack. `CostCalculator` shrinks to courts + signup link management only.

**Tech Stack:** React, TypeScript, Vitest (raw source tests), CSS

---

## File Map

- **Modify:** `signups/frontend/src/pages/AdminSessionDetail.tsx` — merge hero card with controls, add action handlers, single-column layout
- **Modify:** `signups/frontend/src/components/CostCalculator.tsx` — remove controls card, remove `handleToggleActive`/`handleCalculate`/`result` state, remove `onToggleActive`/`onCalculate` from props
- **Modify:** `signups/frontend/src/styles.css` — remove two-column grid media query, remove duplicate/unused styles
- **Modify:** `signups/frontend/src/AdminSessionDetail.test.tsx` — update structure hooks for new class names
- **Modify:** `signups/frontend/src/CostCalculator.test.tsx` — remove `admin-session-controls-card` hook check

---

### Task 1: Update structure tests to reflect new layout

The existing structure tests check for class names that will change. Update them first so we have a failing test target to code toward.

**Files:**
- Modify: `signups/frontend/src/AdminSessionDetail.test.tsx`
- Modify: `signups/frontend/src/CostCalculator.test.tsx`

- [ ] **Step 1: Update AdminSessionDetail structure test**

Replace the entire file content:

```tsx
import { describe, expect, it } from 'vitest'
import AdminSessionDetailSource from './pages/AdminSessionDetail.tsx?raw'

describe('AdminSessionDetail structure hooks', () => {
  it('includes the dedicated admin detail class hooks in the page source', () => {
    expect(AdminSessionDetailSource).toContain('admin-shell')
    expect(AdminSessionDetailSource).toContain('admin-page-header')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-hero')
    expect(AdminSessionDetailSource).toContain('admin-session-detail-stack')
    expect(AdminSessionDetailSource).not.toContain('admin-session-detail-grid')
  })

  it('renders session controls in the hero card', () => {
    expect(AdminSessionDetailSource).toContain('handleToggleActive')
    expect(AdminSessionDetailSource).toContain('handleCalculate')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-costs')
    expect(AdminSessionDetailSource).toContain('admin-session-controls-actions')
  })

  it('renders status badge only once', () => {
    const matches = AdminSessionDetailSource.match(/admin-pill/g)
    // Two occurrences: one in the hero card, one in the loading state (or just one total)
    // The hero card should be the only pill in the main render
    expect(matches).not.toBeNull()
  })
})
```

- [ ] **Step 2: Update CostCalculator structure test**

Replace the entire file content:

```tsx
import { describe, expect, it } from 'vitest'

import CostCalculatorSource from './components/CostCalculator.tsx?raw'

describe('CostCalculator structure hooks', () => {
  it('includes court and signup link class hooks in the source', () => {
    expect(CostCalculatorSource).toContain('admin-court-list')
    expect(CostCalculatorSource).toContain('admin-court-item')
    expect(CostCalculatorSource).toContain('admin-signup-link-card')
  })

  it('does not include session controls card (moved to AdminSessionDetail)', () => {
    expect(CostCalculatorSource).not.toContain('admin-session-controls-card')
    expect(CostCalculatorSource).not.toContain('handleToggleActive')
    expect(CostCalculatorSource).not.toContain('handleCalculate')
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd signups/frontend && npm test
```

Expected: FAIL — `admin-session-detail-stack` not found, `admin-session-detail-grid` still present, `admin-session-controls-card` still in CostCalculator source.

- [ ] **Step 4: Commit failing tests**

```bash
git add signups/frontend/src/AdminSessionDetail.test.tsx signups/frontend/src/CostCalculator.test.tsx
git commit -m "test: update session detail structure tests for merged hero/controls layout"
```

---

### Task 2: Strip CostCalculator down to courts + signup link

Remove the session controls card and its associated state/handlers from `CostCalculator`. The component now only manages courts and the signup link.

**Files:**
- Modify: `signups/frontend/src/components/CostCalculator.tsx`

- [ ] **Step 1: Replace CostCalculator.tsx**

```tsx
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

  async function handleRegenerate() {
    if (!window.confirm('This will invalidate the current link. Continue?')) {
      return
    }
    await regenerateToken(data.session.id)
    onRefresh()
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
```

- [ ] **Step 2: Run tests — CostCalculator test should now pass**

```bash
cd signups/frontend && npm test
```

Expected: CostCalculator structure tests PASS. AdminSessionDetail tests still FAIL.

- [ ] **Step 3: Commit**

```bash
git add signups/frontend/src/components/CostCalculator.tsx
git commit -m "refactor: remove session controls card from CostCalculator"
```

---

### Task 3: Merge hero card with controls in AdminSessionDetail

Add session action handlers to `AdminSessionDetail` and merge the hero card with the cost/action controls. Switch layout to a single vertical stack.

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionDetail.tsx`

- [ ] **Step 1: Replace AdminSessionDetail.tsx**

```tsx
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
    await updateSession(data.session.id, { is_active: !data.session.is_active })
    void load()
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
              <button type="button" className="admin-session-toggle-button" onClick={() => void handleToggleActive()}>
                {data.session.is_active ? 'Close session' : 'Open session'}
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
```

- [ ] **Step 2: Run tests**

```bash
cd signups/frontend && npm test
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add signups/frontend/src/pages/AdminSessionDetail.tsx
git commit -m "feat: merge session controls into hero card, single-column layout"
```

---

### Task 4: Update CSS — single-column stack, remove grid

Replace the two-column grid with a single-column stack. Remove the `admin-session-detail-grid` and `admin-session-detail-panel` rules and the `@media (min-width: 900px)` two-column override.

**Files:**
- Modify: `signups/frontend/src/styles.css`

- [ ] **Step 1: Replace `.admin-session-detail-grid` with `.admin-session-detail-stack`**

Find:
```css
.admin-session-detail-grid {
  display: grid;
  gap: 16px;
}

.admin-session-detail-panel {
  align-self: start;
}
```

Replace with:
```css
.admin-session-detail-stack {
  display: grid;
  gap: 16px;
}
```

- [ ] **Step 2: Remove the two-column media query override**

Find and delete this block entirely:
```css
@media (min-width: 900px) {
  .admin-session-detail-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 24px;
  }
}
```

- [ ] **Step 3: Run tests**

```bash
cd signups/frontend && npm test
```

Expected: All tests PASS.

- [ ] **Step 4: Build to confirm no TypeScript errors**

```bash
cd signups/frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add signups/frontend/src/styles.css
git commit -m "style: replace two-column grid with single-column stack for session detail"
```
