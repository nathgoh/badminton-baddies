# Tailwind Frontend Migration Design

> Date: 2026-03-30
> Status: Approved for planning after user review

## Goal

Migrate the `signups/frontend` app from the current large shared stylesheet to Tailwind CSS, while giving the UI a light visual refresh that feels more expressive and is easier to use on mobile.

This is primarily a presentation-layer migration. The public signup experience should receive the strongest refresh, while the admin pages should move onto the same Tailwind foundation with a cleaner, more utilitarian interpretation of the shared theme.

## Scope

In scope:

- add Tailwind to the Vite frontend build
- replace the current page and component styling approach with Tailwind utilities
- establish a small shared visual theme through Tailwind tokens
- refresh the public signup experience with a mobile-first layout and more personality
- migrate the admin pages to the same Tailwind foundation
- keep any extracted UI primitives minimal and justified by obvious repetition

Out of scope:

- backend or API changes
- changing route structure
- redesigning product workflows
- introducing a full design system or large component library
- preserving the old semantic CSS class structure for compatibility

## Product Direction

### Visual Direction

The frontend should feel:

- warmer and more expressive than the current plain white-and-blue treatment
- clearly structured and easy to scan on phones
- modern but not decorative to the point of harming usability

The public signup surfaces can use stronger gradients, richer card treatments, and more obvious hierarchy. The admin surfaces should be visually related but quieter, with emphasis on clarity and action density.

### Mobile-First Priority

Mobile usability is the primary constraint:

- default to stacked layouts on small screens
- keep form controls and buttons large enough for thumb interaction
- avoid table-like compression for important content
- allow desktop to expand spacing or columns only where it improves readability

Desktop behavior should be an enhancement layer, not the baseline layout being compressed downward.

## Styling Strategy

### Tailwind Foundation

Add Tailwind to the Vite pipeline and replace the current `src/styles.css` page rules with a Tailwind entry stylesheet that contains:

- Tailwind base, components, and utilities directives
- a small amount of app-level base styling
- a minimal set of custom utility or component-layer classes only where repeated utility bundles would otherwise become noisy

The new styling model should be Tailwind-first, not a hybrid where old semantic CSS classes remain the main mechanism.

### Theme Tokens

Define a small Tailwind theme extension for:

- brand and accent colors
- background tones
- border radii
- shadow presets
- any typography tokens needed for the refreshed look

The token layer should be intentionally small. It exists to keep the refresh coherent, not to recreate the current stylesheet in configuration form.

### Primitive Policy

The preferred approach is "as much Tailwind as possible" with only a few reusable wrappers when repetition is clearly hurting readability.

Likely acceptable primitives:

- `Button`
- `Card`
- `Field`
- optionally a thin `PageShell`

These should stay shallow:

- mostly class composition plus standard element props
- no variant explosion
- no general-purpose component system

If a component does not obviously improve readability or reduce duplication across multiple screens, it should remain inline.

## Public Signup Experience

### Goal

Rebuild the public signup flow with a stronger mobile-first hierarchy while preserving current behavior.

Affected surfaces include:

- session hero and availability summary
- signup and roster tab switcher
- court and cost summaries
- signup form
- cancellation panel
- success and status banners

### Layout Direction

The public page should be built around a single-column mobile layout:

- prominent session hero at the top
- clear availability and capacity signal
- segmented signup/roster control with large tap targets
- stacked information cards below

On larger screens, the layout can widen and introduce multi-column sections selectively, but mobile should remain the primary composition model.

### Visual Direction

The public side can carry most of the refresh:

- stronger hero treatment
- richer color accents
- more confident card hierarchy
- cleaner empty and success states

This should still feel trustworthy and legible. The design should not become playful at the expense of form completion or roster readability.

## Admin Experience

### Goal

Move the admin pages onto the same Tailwind foundation so they no longer depend on the legacy stylesheet, while keeping the admin experience cleaner and more restrained than the public side.

Affected pages include:

- `/admin/login`
- `/admin`
- `/admin/sessions/:id`
- `/admin/players`

### Layout Direction

Admin pages should remain task-oriented:

- page containers with consistent spacing
- stacked card sections on mobile
- restrained use of accent color
- wider layouts only where they improve scanning or editing

The admin UI should feel coherent with the public side without inheriting its full visual emphasis.

### Interaction Direction

Admin controls should prioritize:

- obvious primary and secondary actions
- readable roster and player rows on mobile
- predictable card-level grouping for editing and session controls

No admin workflow changes are required. Existing state flow and API interactions should remain intact.

## File And Code Structure

The migration should follow the current React component boundaries where practical:

- keep page components responsible for layout and state wiring
- keep existing behavior-focused child components unless conversion reveals a small simplification
- avoid a large architectural rewrite during a styling migration

Expected structural changes:

- `src/main.tsx` switches to a Tailwind entry stylesheet
- add the Tailwind configuration required by the selected Vite integration and keep the setup to one clear path rather than mixing multiple installation styles
- create a new Tailwind CSS entry file in `src/`
- convert page and component markup to Tailwind utility classes
- delete or reduce the legacy shared stylesheet once no longer needed

If a tiny `src/components/ui/` folder is introduced, it should only contain the minimal wrappers justified by repetition.

## Migration Strategy

Use a staged migration so styling changes do not destabilize behavior:

1. establish Tailwind and the shared theme
2. convert the public signup flow end-to-end
3. convert admin pages onto the same foundation
4. remove remaining legacy stylesheet usage

This order puts the strongest visual payoff first and ensures the most mobile-sensitive surface is intentionally rebuilt rather than translated mechanically.

## Behavior Preservation

The migration should preserve:

- current API usage
- route structure
- form submission behavior
- signup and cancellation flows
- roster and waitlist behavior
- admin editing and session management flows

Markup can change substantially where needed for the new visual structure, but business behavior should remain the same.

## Testing Strategy

The migration should continue to rely on Vitest coverage already present in `signups/frontend/src`.

Testing expectations:

- keep existing behavior tests passing
- update tests that rely on old structure or class hooks only where necessary
- prefer assertions on accessible text, roles, and stable behavior over brittle styling selectors
- add focused tests for any extracted primitive that contains behavior rather than pure styling composition
- run at least a production build and the relevant frontend test suite before claiming completion

This migration is mostly visual, but the main risk is behavior regression caused by markup and interaction changes. Verification should concentrate on forms, tabs, admin controls, and mobile-sensitive layouts.

## Risks And Guardrails

### Main Risks

- class-heavy JSX becoming harder to read than the current CSS approach
- accidental behavior regressions while rebuilding markup
- tests becoming fragile if they depend on presentational details
- the migration turning into an open-ended redesign

### Guardrails

- keep primitives minimal
- keep backend contracts unchanged
- prefer readability over absolute Tailwind purity when duplication becomes obvious
- prioritize mobile usability over desktop density
- remove legacy CSS only after all dependent components are converted
- keep scope focused on the current frontend rather than expanding into unrelated refactors

## Success Criteria

The migration is successful when:

- the frontend builds and tests pass with Tailwind as the primary styling mechanism
- the legacy shared stylesheet is removed or reduced to a minimal Tailwind entry file
- the public signup flow feels noticeably better on mobile
- admin pages are visually coherent and usable on mobile
- the codebase remains mostly Tailwind-driven, with only a very small number of UI primitives
