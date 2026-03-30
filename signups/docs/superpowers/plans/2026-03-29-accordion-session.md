# Accordion Session Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "Manage" navigation button on the Admin Session List with an inline accordion that expands CostCalculator + RosterManager below the clicked row.

**Architecture:** Add `expandedId`/`expandedData` state to `AdminSessionList`. Clicking a session row fetches its detail via `getAdminSession` and renders it inline. The session name becomes a `<Link>` to the existing full-page route. Existing `CostCalculator` and `RosterManager` components are used unchanged.

**Tech Stack:** React 18, TypeScript, React Router v6, Vitest

---

## File Map

| File | Change |
|---|---|
| `signups/frontend/src/utils.ts` | Add `nextExpandedId` helper |
| `signups/frontend/src/utils.test.ts` | Add tests for `nextExpandedId` |
| `signups/frontend/src/pages/AdminSessionList.tsx` | Full rewrite of session list rows |

No other files change.

---

### Task 1: Add and test `nextExpandedId` helper

This pure function encapsulates the accordion toggle logic: returns `null` if clicking the already-expanded session (collapse), otherwise returns the clicked ID (expand).

**Files:**
- Modify: `signups/frontend/src/utils.ts`
- Modify: `signups/frontend/src/utils.test.ts`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `signups/frontend/src/utils.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { formatTime, nextExpandedId } from './utils'

// ... existing formatTime tests ...

describe('nextExpandedId', () => {
  it('returns the clicked id when nothing is expanded', () => {
    expect(nextExpandedId(null, 'abc')).toBe('abc')
  })

  it('returns the clicked id when a different session is expanded', () => {
    expect(nextExpandedId('abc', 'xyz')).toBe('xyz')
  })

  it('returns null when clicking the already-expanded session (collapse)', () => {
    expect(nextExpandedId('abc', 'abc')).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd signups/frontend && npm test
```

Expected: 3 failures — `nextExpandedId is not a function` (or similar import error).

- [ ] **Step 3: Add `nextExpandedId` to utils**

Append to `signups/frontend/src/utils.ts`:

```ts
/** Returns the next expanded session ID for an accordion toggle.
 *  Clicking the already-expanded session collapses it (returns null).
 *  Clicking a different session expands it (returns its id). */
export function nextExpandedId(currentId: string | null, clickedId: string): string | null {
  return currentId === clickedId ? null : clickedId
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd signups/frontend && npm test
```

Expected: all tests pass including the 3 new ones.

- [ ] **Step 5: Commit**

```bash
git add signups/frontend/src/utils.ts signups/frontend/src/utils.test.ts
git commit -m "feat: add nextExpandedId helper for accordion toggle"
```

---

### Task 2: Rewrite session rows in `AdminSessionList` with accordion

Replace the "Manage" button + page navigation with an expandable inline detail panel. Each session row becomes clickable; clicking the same row again collapses it.

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionList.tsx`

- [ ] **Step 1: Replace the file contents**

Replace `signups/frontend/src/pages/AdminSessionList.tsx` entirely with:

```tsx
import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import CostCalculator from '../components/CostCalculator'
import RosterManager from '../components/RosterManager'
import { createCourt, createSession, deleteSession, getAdminSession, listSessions } from '../api/client'
import { useAdminAuth } from '../auth/useAdminAuth'
import { nextExpandedId } from '../utils'
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

export default function AdminSessionList() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [showForm, setShowForm] = useState(false)
  const [sessionName, setSessionName] = useState('')
  const [sessionDate, setSessionDate] = useState('')
  const [cancelWindow, setCancelWindow] = useState('48')
  const [isNarrow, setIsNarrow] = useState(() => window.innerWidth < 900)
  const [courts, setCourts] = useState<NewCourtForm[]>([
    { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' },
  ])
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [expandedData, setExpandedData] = useState<AdminSessionResponse | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const { logout, email } = useAdminAuth()
  const navigate = useNavigate()

  async function load() {
    setSessions(await listSessions())
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    function handleResize() {
      setIsNarrow(window.innerWidth < 900)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  async function handleRowClick(session: Session) {
    const newId = nextExpandedId(expandedId, session.id)
    if (newId === null) {
      setExpandedId(null)
      setExpandedData(null)
    } else {
      const data = await getAdminSession(session.id)
      setExpandedId(session.id)
      setExpandedData(data)
    }
  }

  async function handleExpandedRefresh() {
    if (!expandedId) return
    setExpandedData(await getAdminSession(expandedId))
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

  function rowBackground(sessionId: string) {
    if (expandedId === sessionId) return hoveredId === sessionId ? '#eaedff' : '#f0f4ff'
    return hoveredId === sessionId ? '#f5f6ff' : 'white'
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, fontFamily: 'sans-serif' }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Court Signup Admin</h2>
          <div style={{ fontSize: 12, color: '#888' }}>{email}</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => navigate('/admin/players')}
            style={{ padding: '8px 16px', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', background: 'white' }}
          >
            Players
          </button>
          <button
            onClick={logout}
            style={{ padding: '8px 16px', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', background: 'white' }}
          >
            Sign out
          </button>
        </div>
      </div>

      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}
      >
        <h3 style={{ margin: 0 }}>Sessions</h3>
        <button
          onClick={() => setShowForm(true)}
          style={{ padding: '8px 16px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          + New session
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={handleCreate}
          style={{ border: '1px solid #c5cae9', borderRadius: 8, padding: 20, marginBottom: 24, background: '#f8f9ff' }}
        >
          <h4 style={{ margin: '0 0 16px' }}>New Session</h4>
          {error ? <div style={{ color: '#c62828', marginBottom: 12 }}>{error}</div> : null}
          <div
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}
          >
            <div>
              <label style={{ fontSize: 12 }}>Session name *</label>
              <input
                required
                value={sessionName}
                onChange={(event) => setSessionName(event.target.value)}
                style={{ display: 'block', width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, marginTop: 4, boxSizing: 'border-box', height: 36 }}
              />
            </div>
            <div>
              <label style={{ fontSize: 12 }}>Date *</label>
              <input
                type="date"
                required
                min={new Date().toISOString().slice(0, 10)}
                value={sessionDate}
                onChange={(event) => setSessionDate(event.target.value)}
                style={{ display: 'block', width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, marginTop: 4, boxSizing: 'border-box', height: 36 }}
              />
            </div>
            <div>
              <label style={{ fontSize: 12 }}>Cancel window (hours)</label>
              <input
                type="number"
                value={cancelWindow}
                onChange={(event) => setCancelWindow(event.target.value)}
                style={{ display: 'block', width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, marginTop: 4, boxSizing: 'border-box', height: 36 }}
              />
            </div>
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Courts</div>
          {courts.map((court, index) => (
            <div
              key={index}
              style={{
                display: 'grid',
                gridTemplateColumns: isNarrow
                  ? '1fr'
                  : 'minmax(180px, 2fr) repeat(4, minmax(110px, 1fr)) auto',
                gap: 8,
                marginBottom: 8,
                alignItems: 'stretch',
              }}
            >
              <input
                placeholder="Court name"
                value={court.name}
                onChange={(event) => updateCourt(index, 'name', event.target.value)}
                style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4 }}
              />
              <input
                type="time"
                value={court.start_time}
                onChange={(event) => updateCourt(index, 'start_time', event.target.value)}
                style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4 }}
              />
              <input
                type="time"
                value={court.end_time}
                onChange={(event) => updateCourt(index, 'end_time', event.target.value)}
                style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4 }}
              />
              <input
                placeholder="Max players"
                type="number"
                min="1"
                value={court.max_players}
                onChange={(event) => updateCourt(index, 'max_players', event.target.value)}
                style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4 }}
              />
              <input
                placeholder="Cost $"
                type="number"
                value={court.total_cost}
                onChange={(event) => updateCourt(index, 'total_cost', event.target.value)}
                style={{ padding: 6, border: '1px solid #ddd', borderRadius: 4 }}
              />
              <button
                type="button"
                onClick={() => {
                  if (courts.length === 1) {
                    setError('At least one court is required.')
                    return
                  }
                  setError(null)
                  setCourts((current) => current.filter((_, courtIndex) => courtIndex !== index))
                }}
                style={{
                  padding: '6px 8px',
                  background: 'white',
                  border: '1px solid #ffcdd2',
                  borderRadius: 4,
                  color: '#c62828',
                  cursor: 'pointer',
                  alignSelf: isNarrow ? 'start' : 'stretch',
                  justifySelf: isNarrow ? 'start' : 'stretch',
                }}
              >
                x
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setCourts((current) => [
                ...current,
                { name: '', start_time: '19:00', end_time: '22:00', max_players: '6', total_cost: '' },
              ])
            }
            style={{ fontSize: 12, padding: '4px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', marginBottom: 16 }}
          >
            + Add court
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="submit"
              style={{ padding: '8px 20px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              style={{ padding: '8px 20px', background: 'white', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer' }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      <div style={{ border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden' }}>
        {sessions.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: '#aaa' }}>No sessions yet</div>
        ) : null}
        {sessions.map((session) => (
          <Fragment key={session.id}>
            <div
              onClick={() => void handleRowClick(session)}
              onMouseEnter={() => setHoveredId(session.id)}
              onMouseLeave={() => setHoveredId(null)}
              style={{
                padding: '14px 16px',
                borderBottom: expandedId === session.id ? '1px solid #c5cae9' : '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: rowBackground(session.id),
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: expandedId === session.id ? '#3f51b5' : '#ccc', fontSize: 11 }}>
                  {expandedId === session.id ? '▾' : '▸'}
                </span>
                <div>
                  <Link
                    to={`/admin/sessions/${session.id}`}
                    onClick={(e) => e.stopPropagation()}
                    style={{ color: '#3f51b5', textDecoration: 'none', fontWeight: 600 }}
                  >
                    {session.name}
                  </Link>
                  <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{session.date}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {session.is_active ? (
                  <span
                    style={{ background: '#e8f5e9', color: '#2e7d32', fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 4 }}
                  >
                    Active
                  </span>
                ) : null}
                <button
                  onClick={(e) => { e.stopPropagation(); void handleDelete(session) }}
                  style={{ padding: '6px 12px', background: 'white', border: '1px solid #ffcdd2', borderRadius: 4, cursor: 'pointer', fontSize: 12, color: '#c62828' }}
                >
                  Delete
                </button>
              </div>
            </div>
            {expandedId === session.id && expandedData ? (
              <div style={{ background: '#f8f9ff', borderBottom: '2px solid #c5cae9', padding: 16 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  <CostCalculator data={expandedData} onRefresh={() => void handleExpandedRefresh()} />
                  <RosterManager signups={expandedData.signups} onRefresh={() => void handleExpandedRefresh()} />
                </div>
              </div>
            ) : null}
          </Fragment>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd signups/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run tests**

```bash
cd signups/frontend && npm test
```

Expected: all tests pass (the `nextExpandedId` tests from Task 1 still pass).

- [ ] **Step 4: Smoke test in browser**

```bash
cd signups/frontend && npm run dev
```

Navigate to `http://localhost:5173/admin` (log in if needed).

Verify:
- Session rows are clickable (cursor changes on hover, row tints blue)
- Clicking a row expands the detail panel with CostCalculator + RosterManager
- Clicking the same row again collapses it
- Clicking a different row closes the first and opens the new one
- The session name is a link — clicking it navigates to `/admin/sessions/:id`
- Clicking Delete still works and does not trigger expansion
- The "Active" badge still appears for active sessions

- [ ] **Step 5: Commit**

```bash
git add signups/frontend/src/pages/AdminSessionList.tsx
git commit -m "feat: expand session detail inline as accordion on admin list page"
```
