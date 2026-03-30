# Past Sessions Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Past sessions" section to the admin sessions list that shows sessions with a date before today, using the same card and accordion pattern as upcoming sessions.

**Architecture:** Client-side split only — no backend changes. Add an `isPastSession(date, today)` utility to `utils.ts`, then in `AdminSessionList` derive `upcomingSessions` and `pastSessions` from the existing `sessions` state and render two sections. The existing `expandedId`/`expandedData` state is shared across both sections since session IDs are globally unique.

**Tech Stack:** React, TypeScript, Vitest (raw source tests)

---

## File Map

- **Modify:** `signups/frontend/src/utils.ts` — add `isPastSession` utility function
- **Modify:** `signups/frontend/src/utils.test.ts` — add tests for `isPastSession`
- **Modify:** `signups/frontend/src/pages/AdminSessionList.tsx` — split sessions, rename heading, add past section
- **Modify:** `signups/frontend/src/AdminSessionList.test.tsx` — add structure hooks for new section

---

### Task 1: Add `isPastSession` utility

**Files:**
- Modify: `signups/frontend/src/utils.ts`
- Modify: `signups/frontend/src/utils.test.ts`

- [ ] **Step 1: Write failing tests for `isPastSession`**

Add to the bottom of `signups/frontend/src/utils.test.ts`:

```ts
describe('isPastSession', () => {
  it('returns true when the session date is before today', () => {
    expect(isPastSession('2026-03-28', '2026-03-30')).toBe(true)
  })

  it('returns false when the session date is today', () => {
    expect(isPastSession('2026-03-30', '2026-03-30')).toBe(false)
  })

  it('returns false when the session date is in the future', () => {
    expect(isPastSession('2026-04-05', '2026-03-30')).toBe(false)
  })
})
```

Also update the import at the top of `utils.test.ts` to include `isPastSession`:

```ts
import { describe, it, expect } from 'vitest'
import { formatCancellationStatus, formatDisplayDate, formatTime, isPastSession, nextExpandedId } from './utils'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd signups/frontend && npm test -- utils
```

Expected: FAIL — `isPastSession` is not exported from `./utils`

- [ ] **Step 3: Implement `isPastSession` in utils.ts**

Add to the bottom of `signups/frontend/src/utils.ts`:

```ts
/** Returns true if the session date (YYYY-MM-DD) is before today's date.
 *  A session on today's date is NOT considered past.
 *  Pass `today` explicitly in tests to avoid depending on the system clock. */
export function isPastSession(date: string, today: string = new Date().toISOString().slice(0, 10)): boolean {
  return date < today
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd signups/frontend && npm test -- utils
```

Expected: All `isPastSession` tests PASS

- [ ] **Step 5: Commit**

```bash
git add signups/frontend/src/utils.ts signups/frontend/src/utils.test.ts
git commit -m "feat: add isPastSession utility"
```

---

### Task 2: Split sessions into two sections in AdminSessionList

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionList.tsx`
- Modify: `signups/frontend/src/AdminSessionList.test.tsx`

- [ ] **Step 1: Update the structure test to include the new section**

Replace the entire contents of `signups/frontend/src/AdminSessionList.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import AdminSessionListSource from './pages/AdminSessionList.tsx?raw'

describe('AdminSessionList structure hooks', () => {
  it('includes the mobile-first admin structure class hooks in the page source', () => {
    expect(AdminSessionListSource).toContain('admin-sessions-page')
    expect(AdminSessionListSource).toContain('admin-session-card')
    expect(AdminSessionListSource).toContain('admin-session-form')
    expect(AdminSessionListSource).toContain('admin-court-block')
  })

  it('includes past sessions section', () => {
    expect(AdminSessionListSource).toContain('admin-past-session-list')
    expect(AdminSessionListSource).toContain('pastSessions')
    expect(AdminSessionListSource).toContain('upcomingSessions')
  })
})
```

- [ ] **Step 2: Run tests to verify the new test fails**

```bash
cd signups/frontend && npm test -- AdminSessionList
```

Expected: FAIL — `admin-past-session-list`, `pastSessions`, `upcomingSessions` not found in source

- [ ] **Step 3: Add the import for `isPastSession` in AdminSessionList.tsx**

In `signups/frontend/src/pages/AdminSessionList.tsx`, update the import from `../utils`:

```tsx
import { nextExpandedId, isPastSession } from '../utils'
```

- [ ] **Step 4: Derive upcoming and past sessions before the return statement**

In `AdminSessionList`, right before the `return (` statement (around line 138), add:

```tsx
  const upcomingSessions = sessions.filter((s) => !isPastSession(s.date))
  const pastSessions = sessions.filter((s) => isPastSession(s.date))
```

- [ ] **Step 5: Rename "All sessions" to "Upcoming sessions" in the toolbar**

Find the toolbar section heading:
```tsx
          <h2 className="admin-sessions-toolbar-title">All sessions</h2>
```

Replace with:
```tsx
          <h2 className="admin-sessions-toolbar-title">Upcoming sessions</h2>
```

- [ ] **Step 6: Update the session list to use upcomingSessions**

Find the opening of the session list div:
```tsx
      <div className="admin-session-list">
        {sessions.length === 0 ? (
          <div className="admin-session-empty-state">No sessions yet</div>
        ) : null}

        {sessions.map((session) => {
```

Replace with:
```tsx
      <div className="admin-session-list">
        {upcomingSessions.length === 0 ? (
          <div className="admin-session-empty-state">No sessions yet</div>
        ) : null}

        {upcomingSessions.map((session) => {
```

- [ ] **Step 7: Add the past sessions section after the closing `</div>` of the upcoming session list**

After the `</div>` that closes `<div className="admin-session-list">`, add:

```tsx
      <section className="admin-sessions-toolbar">
        <div>
          <div className="admin-sessions-toolbar-label">History</div>
          <h2 className="admin-sessions-toolbar-title">Past sessions</h2>
        </div>
      </section>

      <div className="admin-session-list admin-past-session-list">
        {pastSessions.length === 0 ? (
          <div className="admin-session-empty-state">No past sessions</div>
        ) : null}

        {pastSessions.map((session) => {
          const isExpanded = expandedId === session.id

          return (
            <Fragment key={session.id}>
              <article className={`admin-session-card${isExpanded ? ' is-expanded' : ''}`}>
                <button
                  className="admin-session-card-main"
                  onClick={() => void handleRowClick(session)}
                  type="button"
                >
                  <div className="admin-session-card-top">
                    <span className="admin-session-card-chevron" aria-hidden="true">
                      {isExpanded ? '▾' : '▸'}
                    </span>
                    <span className={`admin-session-card-status${session.is_active ? ' is-active' : ''}`}>
                      {session.is_active ? 'Active' : 'Draft'}
                    </span>
                  </div>

                  <div className="admin-session-card-copy">
                    <div className="admin-session-card-name">{session.name}</div>
                    <div className="admin-session-card-date">{session.date}</div>
                  </div>

                  <div className="admin-session-card-stats">
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Cancel window</span>
                      <strong>{formatCancelWindow(session.cancel_window_hours)}</strong>
                    </div>
                    <div className="admin-session-card-stat">
                      <span className="admin-session-card-stat-label">Details</span>
                      <strong>{isExpanded ? 'Open' : 'Closed'}</strong>
                    </div>
                  </div>
                </button>

                <div className="admin-session-card-actions">
                  <Link
                    className="admin-session-card-link"
                    onClick={(event) => event.stopPropagation()}
                    to={`/admin/sessions/${session.id}`}
                  >
                    Open details
                  </Link>
                  <button
                    className="admin-sessions-delete-button"
                    onClick={() => void handleDelete(session)}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </article>

              {isExpanded && expandedData ? (
                <div className="admin-session-expanded">
                  <div className="admin-session-expanded-grid">
                    <CostCalculator data={expandedData} onRefresh={() => void handleExpandedRefresh()} />
                    <RosterManager
                      onRefresh={() => void handleExpandedRefresh()}
                      signups={expandedData.signups}
                    />
                  </div>
                </div>
              ) : null}
            </Fragment>
          )
        })}
      </div>
```

- [ ] **Step 8: Run all tests**

```bash
cd signups/frontend && npm test
```

Expected: All 33 tests PASS (32 existing + 1 new)

- [ ] **Step 9: Build to confirm no TypeScript errors**

```bash
cd signups/frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 10: Commit**

```bash
git add signups/frontend/src/pages/AdminSessionList.tsx signups/frontend/src/AdminSessionList.test.tsx
git commit -m "feat: add past sessions section to admin sessions list"
```
