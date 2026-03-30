# Cost Split: Remainder After Adjusted Players

**Date:** 2026-03-30

## Problem

When an admin manually adjusts a player's owed amount (`amount_adjusted=True`), the current "Calculate & assign costs" logic divides the *full* `total_cost` by all confirmed players, then skips adjusted ones. The adjusted players' custom amounts are not subtracted from the pool, so the numbers don't balance.

## Goal

When calculating costs, subtract manually-adjusted amounts from the total first, then split the remainder evenly among the unmodified players.

## Design

### Backend — `admin.py` `calculate_costs`

Replace:
```python
base_amount = round(total_cost / len(confirmed), 2)
for signup in confirmed:
    if not signup.amount_adjusted:
        storage.update_signup(signup.id, SignupUpdate(amount_owed=base_amount))
```

With:
```python
adjusted = [s for s in confirmed if s.amount_adjusted and s.amount_owed is not None]
unadjusted = [s for s in confirmed if not s.amount_adjusted]
adjusted_total = sum(s.amount_owed for s in adjusted)

if not unadjusted:
    if round(adjusted_total, 2) != round(total_cost, 2):
        raise HTTPException(
            status_code=400,
            detail=f"Adjusted amounts (${adjusted_total:.2f}) do not sum to total cost (${total_cost:.2f})"
        )
    return CostCalculationResult(total_cost=total_cost, confirmed_count=len(confirmed), base_amount=0.0)

remaining = total_cost - adjusted_total
base_amount = round(remaining / len(unadjusted), 2)
for signup in unadjusted:
    storage.update_signup(signup.id, SignupUpdate(amount_owed=base_amount))
```

### Error cases

| Scenario | Behaviour |
|---|---|
| Some players adjusted, some not | Remainder split among unmodified players |
| All players adjusted, sum = total_cost | No-op, success (`base_amount=0`) |
| All players adjusted, sum ≠ total_cost | HTTP 400 with descriptive message |
| No confirmed players | Existing 400 ("No confirmed players") — unchanged |

### Frontend

No changes. `handleCalculate` in `CostCalculator.tsx` already `alert()`s the API error message on failure.

### Models/Types

No changes. `CostCalculationResult.base_amount` is already `float`.

## Scope

Single-function backend change only. No new endpoints, models, or UI.
