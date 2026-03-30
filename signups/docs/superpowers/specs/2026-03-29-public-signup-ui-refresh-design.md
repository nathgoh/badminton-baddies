# Public Signup UI Refresh Design

Date: 2026-03-29
Topic: Public signup page visual hierarchy and mobile-safe cancel flow

## Problem

The current public signup page is functional but visually clunky. The session availability text floats above the court cards without a clear container, the court cards visually compete with the signup form even though players do not choose a court, and the cancel flow risks being missed on mobile when placed only at the bottom of the page.

## Goals

- Make the page feel more polished and app-like without introducing a UI framework.
- Improve visual hierarchy so signup remains the primary action.
- Keep court information visible but clearly informational.
- Preserve the required payment agreement checkbox as a real form control.
- Make the cancel flow discoverable on mobile without giving it equal weight to signup.

## Chosen Approach

Keep the existing single-page signup and roster structure, but redesign the public signup tab into a stronger card-based layout:

- a gradient session header with:
  - session chip at the top left
  - session name directly below the chip
  - session date below the name
  - availability card aligned to the top right
- a quieter session summary card below the tabs
- a subdued courts list inside the summary card rather than standalone court tiles
- a visible "Already signed up?" utility row near the top of the signup tab that can reveal the cancel controls inline
- a more polished signup card with preserved field order and checkbox behavior

## Layout Behavior

### Header

- Replace the plain rectangular header with a rounded, gradient hero card.
- Keep the session chip ("Thursday Session") at the top left.
- Place the session name directly under the chip.
- Keep the date below the session name.
- Move the availability card flush to the top right of the header block.
- Availability text should continue to use session-level wording such as `2/3 spots filled`.

### Tabs

- Keep the existing two-tab structure (`Sign Up`, `Roster (n)`).
- Restyle tabs to feel like a segmented control rather than plain text buttons.
- Preserve the current behavior and data loading model.

### Session Summary And Courts

- Replace the current standalone court card grid with a summary card.
- Keep session availability in the summary card using concise status language such as `1 spot left before waitlist`.
- Present courts as low-emphasis rows under a `Courts` label.
- Each court row should show:
  - court name
  - time range
  - capacity label using `spots`, not `players`
- Courts should read as informational metadata, not interactive selections.

### Signup Form

- Keep the existing fields and behavior:
  - email
  - name
  - venmo or phone number
  - required payment agreement checkbox
- Preserve autofill-on-email-blur behavior.
- Preserve active/inactive session behavior.
- Preserve signup success/waitlist messaging.
- Restyle the form container and controls to match the polished visual direction.
- The payment agreement must remain a real checkbox control, not static text.

### Cancel Flow

- Do not rely on a cancel card that appears only at the bottom of the screen.
- Add a visible `Already signed up?` utility row near the top of the signup tab, below the summary card and above the signup form.
- Use that utility row to expand or reveal the cancel controls inline.
- Keep the cancel form secondary in emphasis to signup.
- Preserve current lookup, error, and cancellation behaviors.
- Preserve the cancellation deadline helper text.

## Error Handling

- Existing signup and cancellation errors should remain inline within their respective sections.
- The redesign should not suppress current error messaging paths.
- Expanding the cancel section should not hide errors that appear after lookup or cancel attempts.

## Testing

- Verify the public signup page still renders in both signup and roster tabs.
- Verify the signup form still enforces the payment agreement checkbox.
- Verify court information displays as informational rows with `spots` wording.
- Verify the cancel entry point is visible near the top of the signup tab on mobile-sized widths.
- Verify the cancel section can still perform lookup and cancellation as before.
- Verify the frontend still builds successfully with `npm run build`.

## Constraints

- Follow the existing frontend stack: React 18, TypeScript, Vite, React Router.
- Do not introduce a new component library or styling framework.
- Prefer scoped CSS/classes over further expanding inline style clutter where practical.
- Keep changes focused on the public signup UI; do not redesign admin pages.
