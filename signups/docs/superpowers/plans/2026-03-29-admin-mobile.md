# Admin Mobile-Friendly Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all admin pages usable on mobile phones via a shared `useMobile()` hook and responsive layout adjustments.

**Architecture:** Extract the existing `isNarrow` resize pattern from `AdminSessionList` into a shared `useMobile()` hook (breakpoint: 640px). Thread it through all admin components. All layout decisions remain as inline style conditionals — no new CSS system.

**Tech Stack:** React 18, TypeScript, Vite, Vitest

---

## File Map

| File | Action |
|------|--------|
| `src/hooks/useMobile.ts` | Create — shared hook, returns `true` when viewport ≤ 640px |
| `src/hooks/useMobile.test.tsx` | Create — smoke tests |
| `src/pages/AdminSessionList.tsx` | Modify — remove `isNarrow`, add `useMobile`, fix header/form/expanded panel |
| `src/pages/AdminSessionDetail.tsx` | Modify — fix `1fr 1fr` grid |
| `src/components/CostCalculator.tsx` | Modify — fix add-court form grids |
| `src/components/RosterManager.tsx` | Modify — tap-to-expand confirmed rows, hide grid header |
| `src/pages/AdminPlayers.tsx` | Modify — stacked rows on mobile |

All paths relative to `signups/frontend/`.

---

### Task 1: useMobile hook

**Files:**
- Create: `signups/frontend/src/hooks/useMobile.ts`
- Create: `signups/frontend/src/hooks/useMobile.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `signups/frontend/src/hooks/useMobile.test.tsx`:

```tsx
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { useMobile } from './useMobile'

function Probe() {
  const isMobile = useMobile()
  return <span>{isMobile ? 'mobile' : 'desktop'}</span>
}

describe('useMobile', () => {
  it('returns false in SSR / node environment', () => {
    // window is undefined in vitest node env, so hook returns false
    const markup = renderToStaticMarkup(<Probe />)
    expect(markup).toContain('desktop')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: FAIL — `useMobile` not found.

- [ ] **Step 3: Create the hook**

Create `signups/frontend/src/hooks/useMobile.ts`:

```ts
import { useEffect, useState } from 'react'

export function useMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.innerWidth <= 640,
  )

  useEffect(() => {
    function handleResize() {
      setIsMobile(window.innerWidth <= 640)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return isMobile
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: PASS — 1 test passing.

- [ ] **Step 5: Commit**

```bash
cd signups/frontend && git add src/hooks/useMobile.ts src/hooks/useMobile.test.tsx && git commit -m "feat: add useMobile hook"
```

---

### Task 2: AdminSessionList

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionList.tsx`

- [ ] **Step 1: Replace `isNarrow` with `useMobile`**

In `AdminSessionList.tsx`:

Remove these lines:
```tsx
const [isNarrow, setIsNarrow] = useState(() => window.innerWidth < 900)
```
```tsx
useEffect(() => {
  function handleResize() {
    setIsNarrow(window.innerWidth < 900)
  }
  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [])
```

Add the import and hook call at the top of the component:
```tsx
import { useMobile } from '../hooks/useMobile'
// ...inside component:
const isMobile = useMobile()
```

Replace all remaining references to `isNarrow` with `isMobile`.

- [ ] **Step 2: Fix the header — buttons wrap on mobile**

Find the outermost header `<div>` (the one with `justifyContent: 'space-between'`):

```tsx
<div
  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}
>
```

Replace with:
```tsx
<div
  style={{
    display: 'flex',
    flexDirection: isMobile ? 'column' : 'row',
    justifyContent: 'space-between',
    alignItems: isMobile ? 'flex-start' : 'center',
    gap: isMobile ? 12 : 0,
    marginBottom: 24,
  }}
>
```

- [ ] **Step 3: Fix the new session form — 3-column grid to single column on mobile**

Find the session fields grid div:
```tsx
style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}
```

Replace with:
```tsx
style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}
```

- [ ] **Step 4: Fix the inline expanded panel — side-by-side to stacked on mobile**

Find the expanded panel grid div:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 24 }}>
```

- [ ] **Step 5: Run tests**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: all tests still passing.

- [ ] **Step 6: Commit**

```bash
cd signups/frontend && git add src/pages/AdminSessionList.tsx && git commit -m "feat: responsive AdminSessionList"
```

---

### Task 3: AdminSessionDetail

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionDetail.tsx`

- [ ] **Step 1: Add `useMobile` and fix the grid**

Add the import:
```tsx
import { useMobile } from '../hooks/useMobile'
```

Add the hook call inside the component (after the `const navigate` line):
```tsx
const isMobile = useMobile()
```

Find the side-by-side grid:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 24 }}>
```

- [ ] **Step 2: Run tests**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: all tests passing.

- [ ] **Step 3: Commit**

```bash
cd signups/frontend && git add src/pages/AdminSessionDetail.tsx && git commit -m "feat: responsive AdminSessionDetail"
```

---

### Task 4: CostCalculator

**Files:**
- Modify: `signups/frontend/src/components/CostCalculator.tsx`

- [ ] **Step 1: Add `useMobile` and fix the add-court form grids**

Add the import:
```tsx
import { useMobile } from '../hooks/useMobile'
```

Add the hook call inside the component (after the `const [addingCourt, ...]` line):
```tsx
const isMobile = useMobile()
```

The "Add court" form has two grids. Find the first one:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 6, marginBottom: 6 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr 1fr', gap: 6, marginBottom: 6 }}>
```

Find the second one:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 8 }}>
```

There is also a court edit form with two similar grids. Find the first:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 6 }}>
```

Find the second (edit form):
```tsx
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
```

Replace with:
```tsx
<div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 6, marginBottom: 8 }}>
```

Note: there are two `1fr 1fr` grids in the edit form and two in the add-court form. Since the edit form's two grids appear before the add-court form's two grids in the file, apply `isMobile` to all four occurrences.

- [ ] **Step 2: Run tests**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: all tests passing.

- [ ] **Step 3: Commit**

```bash
cd signups/frontend && git add src/components/CostCalculator.tsx && git commit -m "feat: responsive CostCalculator forms"
```

---

### Task 5: RosterManager — tap-to-expand confirmed rows

**Files:**
- Modify: `signups/frontend/src/components/RosterManager.tsx`

- [ ] **Step 1: Add hook and state**

Add the import:
```tsx
import { useMobile } from '../hooks/useMobile'
```

Inside the component, after `const [editAmount, setEditAmount] = useState('')`:
```tsx
const isMobile = useMobile()
const [mobileExpandedId, setMobileExpandedId] = useState<string | null>(null)
```

- [ ] **Step 2: Hide the grid header on mobile**

Find the header row div (the one with `gridTemplateColumns: '1fr 80px 70px 60px 90px'`):

```tsx
<div
  style={{
    background: '#f5f5f5',
    padding: '8px 14px',
    display: 'grid',
    gridTemplateColumns: '1fr 80px 70px 60px 90px',
    gap: 8,
    fontSize: 11,
    fontWeight: 600,
    color: '#666',
    borderBottom: '1px solid #e0e0e0',
  }}
>
  <span>Player</span>
  <span>Status</span>
  <span>Owes</span>
  <span>Paid</span>
  <span></span>
</div>
```

Wrap it with a conditional:
```tsx
{!isMobile ? (
  <div
    style={{
      background: '#f5f5f5',
      padding: '8px 14px',
      display: 'grid',
      gridTemplateColumns: '1fr 80px 70px 60px 90px',
      gap: 8,
      fontSize: 11,
      fontWeight: 600,
      color: '#666',
      borderBottom: '1px solid #e0e0e0',
    }}
  >
    <span>Player</span>
    <span>Status</span>
    <span>Owes</span>
    <span>Paid</span>
    <span></span>
  </div>
) : null}
```

- [ ] **Step 3: Add mobile tap-to-expand rows for confirmed signups**

The confirmed signups are rendered with `confirmed.map((signup) => (...))`. Replace the entire map block with a version that branches on `isMobile`:

```tsx
{confirmed.map((signup) =>
  isMobile ? (
    <div
      key={signup.id}
      onClick={() =>
        setMobileExpandedId(mobileExpandedId === signup.id ? null : signup.id)
      }
      style={{
        padding: '10px 14px',
        borderBottom: '1px solid #f5f5f5',
        cursor: 'pointer',
        fontSize: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontWeight: 500 }}>{signup.name}</span>
          <span
            style={{
              background: '#e8f5e9',
              color: '#2e7d32',
              fontSize: 9,
              fontWeight: 600,
              padding: '1px 5px',
              borderRadius: 3,
              marginLeft: 6,
            }}
          >
            confirmed
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: signup.amount_adjusted ? '#e65100' : '#333' }}>
            {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '–'}
          </span>
          <span style={{ fontSize: 11, color: signup.paid ? '#2e7d32' : '#bbb' }}>
            {signup.paid ? '✓' : '–'}
          </span>
          <span style={{ fontSize: 11, color: '#bbb' }}>
            {mobileExpandedId === signup.id ? '▾' : '▸'}
          </span>
        </div>
      </div>
      {mobileExpandedId === signup.id ? (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            marginTop: 8,
            paddingTop: 8,
            borderTop: '1px solid #c5cae9',
            display: 'flex',
            gap: 6,
          }}
        >
          <button
            onClick={() => void handleTogglePaid(signup.id, signup.paid)}
            style={{
              flex: 1,
              fontSize: 11,
              padding: 5,
              background: signup.paid ? '#e8f5e9' : 'white',
              color: signup.paid ? '#2e7d32' : '#999',
              border: `1px solid ${signup.paid ? '#a5d6a7' : '#ddd'}`,
              borderRadius: 3,
              cursor: 'pointer',
            }}
          >
            {signup.paid ? 'Paid ✓' : 'Mark paid'}
          </button>
          {editingId === signup.id ? (
            <div style={{ display: 'flex', flex: 1, gap: 4 }}>
              <input
                type="number"
                step="0.01"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                style={{ width: '100%', padding: 4, border: '1px solid #3f51b5', borderRadius: 3, fontSize: 12 }}
                autoFocus
              />
              <button
                onClick={() => void handleSaveAmount(signup.id)}
                style={{ fontSize: 11, padding: '2px 6px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 3, cursor: 'pointer' }}
              >
                Save
              </button>
              <button
                onClick={() => setEditingId(null)}
                style={{ fontSize: 11, padding: '2px 6px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
              >
                x
              </button>
            </div>
          ) : (
            <button
              onClick={() => {
                setEditingId(signup.id)
                setEditAmount(String(signup.amount_owed ?? ''))
              }}
              style={{
                flex: 1,
                fontSize: 11,
                padding: 5,
                background: 'white',
                border: '1px solid #e0e0e0',
                borderRadius: 3,
                cursor: 'pointer',
                color: '#555',
              }}
            >
              Edit $
            </button>
          )}
          <button
            onClick={() => void handleCancel(signup.id)}
            style={{
              flex: 1,
              fontSize: 11,
              padding: 5,
              background: 'white',
              border: '1px solid #ffcdd2',
              borderRadius: 3,
              color: '#c62828',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      ) : null}
    </div>
  ) : (
    // existing desktop row — unchanged
    <div
      key={signup.id}
      style={{
        padding: '10px 14px',
        display: 'grid',
        gridTemplateColumns: '1fr 80px 70px 60px 90px',
        gap: 8,
        alignItems: 'center',
        borderBottom: '1px solid #f5f5f5',
        fontSize: 12,
      }}
    >
      <div>
        <div style={{ fontWeight: 500 }}>{signup.name}</div>
        <div style={{ fontSize: 11, color: '#999' }}>{signup.email}</div>
      </div>
      <div
        style={{
          background: '#e8f5e9',
          color: '#2e7d32',
          fontSize: 10,
          fontWeight: 600,
          padding: '2px 6px',
          borderRadius: 3,
          textAlign: 'center',
        }}
      >
        confirmed
      </div>
      <div>
        {editingId === signup.id ? (
          <input
            type="number"
            step="0.01"
            value={editAmount}
            onChange={(event) => setEditAmount(event.target.value)}
            style={{
              width: '100%',
              padding: 4,
              border: '1px solid #3f51b5',
              borderRadius: 3,
              fontSize: 12,
            }}
            autoFocus
          />
        ) : (
          <span style={{ color: signup.amount_adjusted ? '#e65100' : '#333', fontWeight: 600 }}>
            {signup.amount_owed != null ? `$${signup.amount_owed.toFixed(2)}` : '-'}
            {signup.amount_adjusted ? ' ✎' : ''}
          </span>
        )}
      </div>
      <div>
        <button
          onClick={() => void handleTogglePaid(signup.id, signup.paid)}
          style={{
            fontSize: 11,
            padding: '2px 6px',
            background: signup.paid ? '#e8f5e9' : 'white',
            color: signup.paid ? '#2e7d32' : '#999',
            border: `1px solid ${signup.paid ? '#a5d6a7' : '#ddd'}`,
            borderRadius: 3,
            cursor: 'pointer',
            fontWeight: signup.paid ? 600 : 400,
          }}
        >
          {signup.paid ? 'Paid ✓' : 'Mark paid'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: 4 }}>
        {editingId === signup.id ? (
          <>
            <button
              onClick={() => void handleSaveAmount(signup.id)}
              style={{
                fontSize: 11,
                padding: '2px 6px',
                background: '#3f51b5',
                color: 'white',
                border: 'none',
                borderRadius: 3,
                cursor: 'pointer',
              }}
            >
              Save
            </button>
            <button
              onClick={() => setEditingId(null)}
              style={{
                fontSize: 11,
                padding: '2px 6px',
                background: 'white',
                border: '1px solid #ccc',
                borderRadius: 3,
                cursor: 'pointer',
              }}
            >
              x
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => {
                setEditingId(signup.id)
                setEditAmount(String(signup.amount_owed ?? ''))
              }}
              style={{
                fontSize: 11,
                color: '#555',
                border: '1px solid #e0e0e0',
                borderRadius: 3,
                padding: '2px 6px',
                cursor: 'pointer',
                background: 'white',
              }}
            >
              Edit
            </button>
            <button
              onClick={() => void handleCancel(signup.id)}
              style={{
                fontSize: 11,
                color: '#c62828',
                border: '1px solid #ffcdd2',
                borderRadius: 3,
                padding: '2px 6px',
                cursor: 'pointer',
                background: 'white',
              }}
            >
              x
            </button>
          </>
        )}
      </div>
    </div>
  ),
)}
```

- [ ] **Step 4: Run tests**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: all tests passing.

- [ ] **Step 5: Commit**

```bash
cd signups/frontend && git add src/components/RosterManager.tsx && git commit -m "feat: responsive RosterManager with tap-to-expand"
```

---

### Task 6: AdminPlayers — stacked rows on mobile

**Files:**
- Modify: `signups/frontend/src/pages/AdminPlayers.tsx`

- [ ] **Step 1: Add `useMobile`**

Add the import:
```tsx
import { useMobile } from '../hooks/useMobile'
```

Inside the component, after `const navigate = useNavigate()`:
```tsx
const isMobile = useMobile()
```

- [ ] **Step 2: Hide the grid header on mobile**

Find the header row div:
```tsx
<div
  style={{
    background: '#f5f5f5',
    padding: '10px 16px',
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr 1fr 80px',
    gap: 8,
    fontSize: 11,
    fontWeight: 600,
    color: '#666',
    borderBottom: '1px solid #e0e0e0',
  }}
>
  <span>Email</span>
  <span>Name</span>
  <span>Venmo / Phone</span>
  <span>First seen</span>
  <span></span>
</div>
```

Wrap it:
```tsx
{!isMobile ? (
  <div
    style={{
      background: '#f5f5f5',
      padding: '10px 16px',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1fr 1fr 80px',
      gap: 8,
      fontSize: 11,
      fontWeight: 600,
      color: '#666',
      borderBottom: '1px solid #e0e0e0',
    }}
  >
    <span>Email</span>
    <span>Name</span>
    <span>Venmo / Phone</span>
    <span>First seen</span>
    <span></span>
  </div>
) : null}
```

- [ ] **Step 3: Add mobile row layout**

The player rows are rendered with `players.map((player) => (...))`. Replace the entire map block with a version that branches on `isMobile`.

The outer row `<div>` changes on mobile: replace the 5-column grid with a flex layout:

```tsx
{players.map((player) => (
  <div
    key={player.email}
    style={
      isMobile
        ? {
            padding: '12px 14px',
            borderBottom: '1px solid #f5f5f5',
            fontSize: 13,
          }
        : {
            padding: '10px 16px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr 1fr 80px',
            gap: 8,
            alignItems: 'center',
            borderBottom: '1px solid #f5f5f5',
            fontSize: 13,
          }
    }
  >
    {isMobile ? (
      editingEmail === player.email ? (
        <>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>{player.email}</div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
            <input
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              placeholder="Name"
              style={{ flex: 1, padding: 6, border: '1px solid #3f51b5', borderRadius: 3, fontSize: 13 }}
            />
            <input
              value={editVenmo}
              onChange={(event) => setEditVenmo(event.target.value)}
              placeholder="Venmo / Phone"
              style={{ flex: 1, padding: 6, border: '1px solid #3f51b5', borderRadius: 3, fontSize: 13 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => void handleSave(player.email)}
              style={{ fontSize: 12, padding: '4px 10px', background: '#3f51b5', color: 'white', border: 'none', borderRadius: 3, cursor: 'pointer' }}
            >
              Save
            </button>
            <button
              onClick={() => setEditingEmail(null)}
              style={{ fontSize: 12, padding: '4px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontWeight: 500 }}>{player.name || '—'}</div>
            <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{player.email}</div>
            {player.venmo_or_phone ? (
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{player.venmo_or_phone}</div>
            ) : null}
            <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>
              {player.first_seen.split('T')[0]}
            </div>
          </div>
          <button
            onClick={() => {
              setEditingEmail(player.email)
              setEditName(player.name)
              setEditVenmo(player.venmo_or_phone)
            }}
            style={{ fontSize: 12, padding: '4px 10px', background: 'white', border: '1px solid #ccc', borderRadius: 3, cursor: 'pointer' }}
          >
            Edit
          </button>
        </div>
      )
    ) : (
      // desktop layout — unchanged
      <>
        <div style={{ fontSize: 12, color: '#555' }}>{player.email}</div>
        {editingEmail === player.email ? (
          <>
            <input
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              style={{ padding: 4, border: '1px solid #3f51b5', borderRadius: 3 }}
            />
            <input
              value={editVenmo}
              onChange={(event) => setEditVenmo(event.target.value)}
              style={{ padding: 4, border: '1px solid #3f51b5', borderRadius: 3 }}
            />
            <div style={{ fontSize: 11, color: '#888' }}>{player.first_seen.split('T')[0]}</div>
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                onClick={() => void handleSave(player.email)}
                style={{
                  fontSize: 11,
                  padding: '2px 6px',
                  background: '#3f51b5',
                  color: 'white',
                  border: 'none',
                  borderRadius: 3,
                  cursor: 'pointer',
                }}
              >
                Save
              </button>
              <button
                onClick={() => setEditingEmail(null)}
                style={{
                  fontSize: 11,
                  padding: '2px 6px',
                  background: 'white',
                  border: '1px solid #ccc',
                  borderRadius: 3,
                  cursor: 'pointer',
                }}
              >
                x
              </button>
            </div>
          </>
        ) : (
          <>
            <div>{player.name}</div>
            <div>{player.venmo_or_phone}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{player.first_seen.split('T')[0]}</div>
            <button
              onClick={() => {
                setEditingEmail(player.email)
                setEditName(player.name)
                setEditVenmo(player.venmo_or_phone)
              }}
              style={{
                fontSize: 11,
                padding: '4px 8px',
                background: 'white',
                border: '1px solid #ccc',
                borderRadius: 3,
                cursor: 'pointer',
              }}
            >
              Edit
            </button>
          </>
        )}
      </>
    )}
  </div>
))}
```

- [ ] **Step 4: Run all tests**

```bash
cd signups/frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Expected: all tests passing.

- [ ] **Step 5: Commit**

```bash
cd signups/frontend && git add src/pages/AdminPlayers.tsx && git commit -m "feat: responsive AdminPlayers"
```
