# Admin Mobile-Friendly Design

**Date:** 2026-03-29

## Overview

Make all admin pages usable on mobile phones. The admin is used both for day-of management (checking roster, marking paid, cancelling players) and for setup (creating sessions, adding courts), so all views need to work well on small screens.

## Approach

Extend the existing JS resize pattern already present in `AdminSessionList`. Extract it into a shared `useMobile()` hook. All layout decisions remain as inline style conditionals — consistent with the existing codebase style.

**No CSS media queries, no new styling system.**

## Shared Hook

New file: `signups/frontend/src/hooks/useMobile.ts`

```ts
export function useMobile(): boolean
```

Returns `true` when `window.innerWidth <= 640px`. Uses a resize event listener, cleaned up on unmount. The existing `isNarrow` state + listener in `AdminSessionList` is deleted and replaced with this hook.

Breakpoint: **640px** — covers all common phones in portrait orientation.

## Component Changes

### AdminSessionList

- **Header:** On mobile, the `Players` and `Sign out` buttons wrap below the title/email block instead of sitting side-by-side.
- **New session form:** Session fields (`name / date / cancel window`) switch from a 3-column grid to single column.
- **Inline expanded panel:** The `1fr 1fr` side-by-side grid (CostCalculator + RosterManager) becomes a single column on mobile — CostCalculator stacked above RosterManager.

### AdminSessionDetail

- The `1fr 1fr` grid switches to single column on mobile (same stacking as above).

### CostCalculator

- The "Add court" form uses multi-column grids that switch to single column on mobile.
- The rest of the component is already single-column content and needs no changes.

### RosterManager

- **Confirmed roster table:** The fixed 5-column grid header is hidden on mobile. Each confirmed player row switches to a two-line tap-to-expand layout:
  - **Collapsed:** name + confirmed badge on the left, amount owed + paid indicator + expand chevron on the right.
  - **Expanded (tap to toggle):** action buttons appear below — Paid toggle, Edit $, Cancel.
- **Waitlist rows:** The existing `1fr auto auto` layout works fine on mobile and is unchanged.

### AdminPlayers

- The 5-column grid header is hidden on mobile.
- Each player row becomes a stacked layout on mobile: email + name + venmo/phone displayed vertically, with date and Edit button on the right side.

## What Is Not Changed

- The public signup page — already mobile-friendly.
- The admin login page — already simple and works on mobile.
- Any backend code.
