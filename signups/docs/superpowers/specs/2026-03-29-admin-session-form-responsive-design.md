# Admin Session Form Responsive Design

Date: 2026-03-29
Topic: Admin session creation form court-row responsiveness

## Problem

The court-entry row in the admin session creation form overflows horizontally on narrower browser widths. The current implementation uses a single grid row with enough minimum-width fields that the layout cannot shrink to fit inside the card.

## Chosen Approach

Keep the current horizontal multi-column court-entry layout on wider screens, but switch each court entry to a stacked vertical layout below a breakpoint.

## Behavior

- Desktop and wide tablet widths:
  - preserve the existing single-row grid layout for each court entry
- Narrower widths:
  - render each court entry as a vertically stacked block
  - keep the field order:
    - court name
    - start
    - end
    - max players
    - cost
    - remove button
- The stacked layout should remain inside the form card without horizontal overflow.

## Constraints

- Do not redesign the overall admin session page.
- Do not change the create-session flow or API behavior.
- Keep the fix local to the admin session form implementation.
- Preserve current desktop usability.

## Implementation Direction

- Add responsive layout logic in the frontend session form only.
- Use a viewport-width check in component state or a responsive CSS approach scoped to this form.
- Apply stacked layout only below the chosen narrow-screen threshold.

## Testing

- Verify the form still builds with `npm run build`.
- Verify the desktop layout remains unchanged.
- Verify the narrow-width layout stacks fields and stays within the card.
