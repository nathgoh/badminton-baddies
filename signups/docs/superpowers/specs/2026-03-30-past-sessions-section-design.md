# Past Sessions Section Design

**Date:** 2026-03-30
**Status:** Approved

## Problem

The admin sessions list shows all sessions in a single flat list with no distinction between upcoming and past sessions. As sessions accumulate, it becomes harder to find current sessions.

## Definition

A session is **past** if its `date` field (ISO `YYYY-MM-DD` string) is strictly before today's local date. A session on today's date is considered upcoming.

## Design

### Data split

No backend changes. The existing `listSessions()` call returns all sessions. In `AdminSessionList`, split the result into two arrays using a utility function:

```ts
// In utils.ts
export function isPastSession(session: Session, today = todayString()): boolean {
  return session.date < today
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10)
}
```

ISO date strings compare correctly lexicographically, so no `Date` parsing is needed. `today` is injectable for testing.

In the component:
```ts
const upcomingSessions = sessions.filter((s) => !isPastSession(s))
const pastSessions = sessions.filter(isPastSession)
```

### UI structure

Two sections, same card and accordion pattern:

1. **Upcoming sessions** — existing toolbar section, renamed from "All sessions" to "Upcoming sessions". Keeps the "+ New session" button. Keeps the existing empty state ("No sessions yet").

2. **Past sessions** — new section below, with its own heading ("Past sessions"). Uses the same `admin-session-card` cards and the existing expand/collapse behaviour. Empty state: "No past sessions" (rendered only when `pastSessions.length === 0`).

### Expand state

The existing `expandedId` / `expandedData` state is shared across both sections — session IDs are globally unique so this works without changes.

### Sorting

Both sections show sessions in the order returned by the API (the backend already returns them in a consistent order — no client-side sort changes needed).

## Files affected

- `signups/frontend/src/utils.ts` — add `isPastSession` utility
- `signups/frontend/src/pages/AdminSessionList.tsx` — split sessions, rename heading, add past section
- `signups/frontend/src/AdminSessionList.test.tsx` — update structure hook for new class names

## Out of scope

- Collapsing/hiding past sessions section
- Backend filtering
- Sorting changes
