# Admin Session Detail UI Cleanup

**Date:** 2026-03-30
**Status:** Approved

## Problem

The session detail page has three issues:
1. The ACTIVE/DRAFT status badge appears three times (page header, hero card, CostCalculator controls card)
2. The hero card and CostCalculator controls card duplicate information (confirmed count, date, etc.)
3. The two-column grid is not mobile-friendly

## Design

### Page layout

All sections stack vertically in a single column. The two-column grid is removed.

Order:
1. Page header
2. Merged hero/controls card
3. Courts card
4. Signup link card
5. Roster card
6. Waitlist card (conditional)

### Page header

Remove the status badge from the page header — it moves to the hero card. Keep the back link, name (`h1`), and summary line (date · confirmed · waitlisted).

### Merged hero/controls card

Combines the existing `admin-session-detail-hero` card and the `admin-session-controls-card` from `CostCalculator` into a single card in `AdminSessionDetail.tsx`.

Contains:
- Card label ("Overview") + status badge (single instance on the page)
- Meta grid: Date, Capacity, Confirmed, Waitlist, Cancel window
- Cost split section: Total court cost, Base per player (shown after calculation)
- Actions: Open/Close session button, Calculate & assign costs button

The Courts count and Public link "Ready/Missing" stats are dropped from the controls — they are visible in the Courts and Signup link cards below.

### CostCalculator component

The `admin-session-controls-card` section is removed from `CostCalculator`. The component now renders only:
- Courts card (`admin-courts-card`)
- Signup link card (`admin-signup-link-card`)

The `handleToggleActive`, `handleCalculate`, and `result` state move up to `AdminSessionDetail`, which passes them as props or callbacks.

### Props changes

`CostCalculator` loses responsibility for the controls card. Two options:
- **A (simpler):** Pass `onToggleActive` and `onCalculate` callbacks and `result` state down as props — keeps logic in CostCalculator, renders in AdminSessionDetail
- **B (cleaner):** Move `handleToggleActive` and `handleCalculate` logic into `AdminSessionDetail` directly, pass only `onRefresh` to CostCalculator

**Chosen: Option B.** The session-level actions (toggle active, calculate costs) belong at the page level. CostCalculator shrinks to court/link management only.

## Files affected

- `signups/frontend/src/pages/AdminSessionDetail.tsx` — merged hero card, single-column layout, session action handlers
- `signups/frontend/src/components/CostCalculator.tsx` — remove controls card and its handlers/state
- `signups/frontend/src/styles.css` — remove two-column grid styles, add single-column layout

## Out of scope

- Inline editing of session fields (Date, Capacity, Cancel window) — the hero card structure is kept as a placeholder for this future work
- Any changes to the Roster or Waitlist sections
