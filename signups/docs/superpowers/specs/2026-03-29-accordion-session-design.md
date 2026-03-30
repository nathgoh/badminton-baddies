# Accordion Session Detail — Design Spec

**Date:** 2026-03-29
**Status:** Approved

## Overview

Replace the "Manage" button navigation on the Admin Session List with an inline accordion. Clicking a session row expands a detail panel (CostCalculator + RosterManager) directly below it. The separate full-page route (`/admin/sessions/:id`) is retained and linked from the session name.

## Interaction Model

- **Row click** (anywhere except the session name link or Delete button) toggles the accordion open/closed.
- **One session open at a time.** Opening a new row auto-closes the previously open one.
- **Session name** is a `<Link>` to `/admin/sessions/:id` — navigates to the existing full-page detail view. The link calls `event.stopPropagation()` so clicking the name does not expand the row.
- **Delete button** calls `event.stopPropagation()` so clicking it does not expand the row.
- The "Manage" button is removed.

## Visual Design

- **Collapsed row:** white background, grey chevron (▸), hover tint `#f5f6ff`.
- **Expanded row:** blue tint `#f0f4ff`, blue chevron (▾), hover tint `#eaedff`, bottom border `#c5cae9`.
- **Detail panel:** `#f8f9ff` background, 2-column grid (CostCalculator left, RosterManager right), `2px solid #c5cae9` bottom border to close off the panel visually.

## State Changes to `AdminSessionList`

Two new state variables:

```ts
const [expandedId, setExpandedId] = useState<string | null>(null)
const [expandedData, setExpandedData] = useState<AdminSessionResponse | null>(null)
```

**Toggle logic on row click:**

```ts
async function handleRowClick(session: Session) {
  if (expandedId === session.id) {
    setExpandedId(null)
    setExpandedData(null)
  } else {
    const data = await getAdminSession(session.id)
    setExpandedId(session.id)
    setExpandedData(data)
  }
}
```

**Refresh callback** passed to CostCalculator and RosterManager re-fetches only `expandedData`:

```ts
async function handleExpandedRefresh() {
  if (!expandedId) return
  setExpandedData(await getAdminSession(expandedId))
}
```

## Components

| Component | Change |
|---|---|
| `AdminSessionList.tsx` | Add accordion state + toggle logic, render detail panel inline, remove "Manage" button, add session name link, add hover + chevron styles |
| `AdminSessionDetail.tsx` | No changes |
| `CostCalculator.tsx` | No changes |
| `RosterManager.tsx` | No changes |

## Routing

The `/admin/sessions/:id` route and `AdminSessionDetail` page are unchanged. The session name in the list links to it. The accordion is the primary interaction; the full page remains available for direct URL access or when a focused view is preferred.

## Out of Scope

- Loading/error states while fetching expanded data (can be added later if needed)
- Persisting the expanded session across page refresh
- Animating the accordion open/close
