# Admin Sessions Mobile Design

Date: 2026-03-30
Topic: Mobile-first redesign of the `/admin` sessions page

## Problem

The current admin sessions page is usable on desktop but not well-suited to phones. The session list still behaves like a dense row/table layout, the create-session form relies on grid rows that become cramped on narrow screens, and the expanded cost/roster tools are still essentially desktop components being compressed.

## Scope

This redesign applies only to the main admin sessions page (`/admin`).

Out of scope for this pass:
- `/admin/sessions/:id`
- `/admin/players`
- authentication flow behavior
- backend/API changes

## Goals

- Make the sessions page feel intentionally mobile-friendly instead of desktop UI collapsed to one column.
- Preserve the current admin workflow:
  - list sessions
  - create sessions
  - expand a session for inline cost/roster tools
  - delete sessions
- Improve touch targets, visual hierarchy, and readability on small screens.

## Chosen Approach

Use a card-first mobile layout:

- stacked session cards instead of row/table-like list entries
- inline expanded details as a vertical continuation below the selected card
- full-width new-session form card with one court per block on mobile

Desktop can remain denser, but mobile is the primary constraint for the redesign.

## Layout Behavior

### Header

- Replace the simple top row with a more structured admin header section.
- Keep:
  - page title
  - signed-in email
  - `Players`
  - `Sign out`
- On mobile:
  - title/email stack vertically
  - action buttons remain easy to tap and visually grouped

### Sessions List

- Replace session rows with stacked cards.
- Each session card should show:
  - session name
  - date
  - active badge if applicable
  - compact stats strip (player count, court count, or equivalent summary already available)
  - primary expand action
  - delete action as a secondary/destructive control
- The card should feel like a standalone unit rather than a row inside a table.

### Expanded Session Content

- Keep inline expansion on the same page.
- On mobile, expanded details should become a vertical continuation below the card.
- The expanded content order should be:
  - cost calculator
  - roster manager
- Do not use a two-column layout on mobile for expanded session content.

### New Session Form

- Keep the create flow on the sessions page.
- Restyle the form as a full-width card.
- Session-level fields should stack vertically on mobile.
- Courts should no longer appear as a dense multi-column row on mobile.
- Each court should render as its own bordered block containing:
  - court name
  - start time
  - end time
  - max players
  - cost
  - remove button
- Add/remove court actions should be clearly separated and easy to tap.

## Interaction Rules

- Expanding and collapsing a session should still work inline.
- Only one session should remain expanded at a time, preserving current behavior.
- Delete remains available but should be visually secondary to expand/open actions.
- No workflow changes are required for session creation or expansion logic.

## Constraints

- Keep the current frontend stack and existing data flow.
- Avoid introducing a new UI framework.
- Keep behavior changes minimal; prioritize layout and interaction clarity.
- Follow established code patterns where reasonable, but prefer class-based/scoped styling over further inline-style growth.

## Testing

- Verify session cards remain readable and tappable on narrow widths.
- Verify expanded session detail stacks vertically on mobile.
- Verify the new-session form remains fully usable on mobile.
- Verify the existing expand/delete/create workflows still work.
- Verify the frontend still builds successfully with `npm run build`.
