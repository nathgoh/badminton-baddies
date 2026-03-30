# Public Roster UI Refresh Design

Date: 2026-03-29
Topic: Public roster tab visual refresh to match the polished signup UI

## Problem

The current public roster tab is functional but visually inconsistent with the refreshed signup tab. It still reads like a simple utility list with bordered rows and status labels, while the signup tab now has a more polished card-based layout and stronger visual hierarchy.

## Goals

- Match the roster tab to the refreshed public signup visual style.
- Keep the roster easy to scan on mobile.
- Present confirmed and waitlist players as clean public-facing lists, not admin-like tables.
- Avoid redundant labels and status pills.

## Chosen Approach

Keep the existing public roster behavior and data model, but restyle the roster tab into two summary cards that sit within the same refreshed page shell:

- confirmed players in a primary neutral card
- waitlist players in a secondary warm-accent card
- row-level position markers retained
- redundant right-side status pills removed

## Layout Behavior

### Shared Shell

- Reuse the refreshed public page shell:
  - gradient hero
  - date and availability card
  - segmented signup/roster tabs

### Confirmed Section

- Render confirmed players inside a single rounded card.
- Use a small uppercase `Confirmed` label and a short summary line such as `3 players in this session`.
- Keep numbered row markers (`1`, `2`, `3`) on the left.
- Use simple row separators rather than boxed mini-cards.

### Waitlist Section

- Render waitlisted players in a separate rounded card with a warm accent color.
- Use a small uppercase `Waitlist` label and a short summary line such as `1 player waiting`.
- Keep row markers like `W1`, `W2` at the row level only.
- Do not repeat waitlist position in a separate header pill.

### Redundancy Rules

- Do not show a `Full` pill in the confirmed section header.
- Do not show a header-level `W1` badge in the waitlist section.
- Let the section summaries communicate counts, and let row markers communicate position.

## Empty States

- Preserve current empty-state behavior when confirmed players are absent.
- Waitlist section remains hidden when there are no waitlisted players.

## Constraints

- Keep the public roster tab read-only.
- Do not expose private player information.
- Do not change roster ordering logic.
- Follow the existing frontend stack and styling approach.

## Testing

- Verify the roster tab still displays confirmed players in signup order.
- Verify waitlisted players still display in waitlist order with `W1`, `W2`, etc.
- Verify the roster shares the refreshed public shell styling.
- Verify redundant header pills are removed.
- Verify the frontend still builds successfully with `npm run build`.
