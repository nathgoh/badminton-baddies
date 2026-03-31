# Automatic Cost Recalculation Design

> Date: 2026-03-30
> Status: Approved for planning after user review

## Goal

Remove the manual "Calculate costs" step from the admin workflow and make player owed amounts recalculate automatically whenever the confirmed-player cost allocation changes.

The system should automatically recalculate costs after:

- a new public signup that lands as `confirmed`
- cancellation of a confirmed signup
- admin promotion from waitlist to confirmed
- admin manual owed modification

Manual owed edits must remain sticky, and the remainder of the session cost should be redistributed across the other confirmed players that are not manually adjusted.

## Current Problem

Today, the backend only recalculates costs when an admin explicitly triggers the calculate action. That creates two issues:

- session owed amounts can become stale after signup, cancellation, promotion, or manual adjustment
- the admin UI needs a separate calculate button to restore consistency

This is unnecessary operational work and makes the real session state depend on whether an admin remembered to press a button.

## Product Direction

The system should treat cost allocation as an invariant, not a manual maintenance step.

Whenever the confirmed-player pool changes or a confirmed player’s manually adjusted amount changes, the backend should immediately recompute the session allocation. The frontend should then simply display refreshed data rather than offering a separate "calculate" action.

## Allocation Rules

### Confirmed Players Only

Only confirmed signups participate in session cost allocation.

- waitlisted signups do not receive `amount_owed`
- cancelled signups do not participate in the calculation

### Adjusted Players Stay Fixed

If a confirmed signup has:

- `amount_adjusted = true`
- and a non-null `amount_owed`

then that player’s amount is treated as fixed input to the calculation and is not overwritten during automatic recalculation.

### Unadjusted Players Split The Remainder

For confirmed signups with `amount_adjusted = false`, the backend should:

1. compute total session cost from courts
2. sum the fixed adjusted amounts
3. subtract adjusted total from session total
4. divide the remainder evenly across all unadjusted confirmed players

This preserves manual overrides while keeping the overall session total balanced.

### No Negative Allocation

If the adjusted total exceeds the total session cost, the recalculation should fail and the triggering action should return a clear error. The system must not silently produce negative or nonsensical per-player amounts.

### No Unadjusted Confirmed Players

If there are confirmed players but all of them are adjusted:

- validate that the adjusted total does not exceed the session total
- do not overwrite any existing adjusted values
- allow the operation if the total is valid

This keeps the current adjusted values intact without inventing a remainder target that no player owns.

## Trigger Points

The backend should invoke the shared recalculation logic after these successful state changes:

### Public Signup

When a public signup is created and its final status is `confirmed`, recalculate the session immediately after persisting the signup.

If the signup lands on the waitlist, do not recalculate because the confirmed-player pool did not change.

### Cancellation

When a confirmed signup is cancelled, the backend should treat cancellation plus any automatic waitlist promotion as one combined roster-change event.

The sequence should be:

1. persist the cancellation
2. auto-promote the next waitlisted signup if one exists
3. recalculate once against the final confirmed roster

If no promotion occurs, recalculate once against the reduced confirmed roster.

If a waitlisted signup is cancelled, no recalculation is needed because confirmed allocation is unchanged.

### Waitlist Promotion

When an admin promotes a signup from waitlist to confirmed, recalculate immediately after promotion.

### Manual Owed Edit

When an admin manually updates `amount_owed` for a confirmed signup, that signup becomes adjusted input and the remainder must be redistributed across the other unadjusted confirmed players immediately.

This is the core product rule requested by the user.

## Backend Architecture

### Shared Recalculation Function

The cost-allocation logic should live in one backend helper/function and be called from all relevant mutation paths.

This function should:

- load the session and confirmed signups
- separate adjusted and unadjusted confirmed players
- validate total cost constraints
- update unadjusted confirmed signups with recalculated `amount_owed`

This avoids duplicating pricing logic across routes and ensures all mutation flows preserve the same invariant.

### Existing Manual Endpoint

The existing manual calculate endpoint should stop being the only path to consistency.

Two acceptable backend options:

- keep the endpoint temporarily as a thin wrapper around the shared recalculation function for compatibility
- or remove/deprecate it once the frontend no longer uses it

For this change, the frontend will remove the button either way.

## Frontend Changes

### Remove Manual Calculate Button

The admin session detail screen should no longer show a calculate-costs action button.

The UI should rely on automatic backend recalculation and refreshed session data.

### Keep Existing Refresh Flow

The frontend already refreshes session data after relevant admin actions. That should remain in place.

After:

- signup success
- cancellation
- waitlist promotion
- manual owed modification

the UI should fetch updated session data and render the recalculated owed amounts without any extra admin step.

## Error Handling

The main new failure mode is adjusted total exceeding total session cost.

When that happens:

- the triggering backend action should fail clearly
- the frontend should surface the returned error message
- no partial negative cost allocation should be persisted

This is especially important for manual owed edits, because that is the user-controlled path that can create invalid totals.

## Testing Strategy

Backend tests should be the primary verification target.

Required coverage:

- confirmed signup triggers recalculation
- waitlist signup does not trigger recalculation
- confirmed cancellation triggers exactly one recalculation against the final post-cancellation roster
- confirmed cancellation with auto-promotion triggers exactly one recalculation against the final post-promotion roster
- waitlist cancellation does not trigger recalculation
- waitlist promotion triggers recalculation
- manual owed edit redistributes the remainder across unadjusted confirmed players
- all-adjusted confirmed players remain unchanged when totals are valid
- adjusted total greater than total session cost returns an error and does not persist invalid values

Frontend coverage should confirm:

- the calculate button is removed from admin session detail
- existing refresh flows still surface updated owed amounts correctly

## Scope

In scope:

- automatic backend recalculation on the specified triggers
- removal of the manual calculate button from the frontend
- backend and frontend tests needed to prove the new behavior

Out of scope:

- redesigning cost allocation beyond the agreed adjusted-plus-remainder model
- changing how paid status works
- changing signup/waitlist business rules unrelated to cost allocation

## Success Criteria

This change is successful when:

- cost allocation updates automatically after every relevant confirmed-pool or manual-amount change
- manual adjusted values remain fixed while the remainder redistributes across the other unadjusted confirmed players
- the admin no longer needs a calculate-costs button
- invalid adjusted totals fail clearly instead of persisting broken amounts
- tests cover the new trigger behavior and pass
