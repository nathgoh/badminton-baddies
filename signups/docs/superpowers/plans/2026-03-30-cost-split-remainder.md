# Cost Split Remainder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When calculating costs, subtract manually-adjusted player amounts from the total first, then split the remainder evenly among unmodified players.

**Architecture:** Single backend change in `calculate_costs` — split confirmed players into adjusted/unadjusted, subtract adjusted totals from pool, divide remainder. Error if all players are adjusted but don't sum to total cost.

**Tech Stack:** Python, FastAPI, pytest

---

## File Map

- Modify: `signups/backend/routers/admin.py` — `calculate_costs` function (lines 90–112)
- Create: `signups/backend/tests/test_calculate_costs.py` — new test file for this endpoint

---

### Task 1: Write failing tests for the new calculation logic

**Files:**
- Create: `signups/backend/tests/test_calculate_costs.py`

- [ ] **Step 1: Create the test file**

```python
# signups/backend/tests/test_calculate_costs.py
from datetime import date

import pytest
from fastapi.testclient import TestClient

from ..models import CourtCreate, SessionCreate, SignupCreate, SignupUpdate
from ..storage.memory import InMemoryAdapter


def _setup(storage: InMemoryAdapter) -> str:
    """Create a session with one court ($30 total) and return the session id."""
    session = storage.create_session(SessionCreate(name="Test", date=date.today(), is_active=True))
    storage.create_court(CourtCreate(session_id=session.id, name="Court 1", start_time="19:00", end_time="22:00", max_players=6, total_cost=30.0))
    return session.id


def test_calculate_costs_splits_evenly_with_no_adjusted_players(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    s3 = storage.create_signup(SignupCreate(session_id=session_id, email="c@x.com", name="C", payment_agreed=True))

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 200
    data = response.json()
    assert data["base_amount"] == 10.0
    # All three updated
    for signup_id in [s1.id, s2.id, s3.id]:
        signup = storage._signups[signup_id]
        assert signup.amount_owed == 10.0


def test_calculate_costs_subtracts_adjusted_player_from_pool(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    s3 = storage.create_signup(SignupCreate(session_id=session_id, email="c@x.com", name="C", payment_agreed=True))
    # A is manually adjusted to $6 — remaining $24 split between B and C = $12 each
    storage.update_signup(s1.id, SignupUpdate(amount_owed=6.0, amount_adjusted=True))

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 200
    data = response.json()
    assert data["base_amount"] == 12.0
    assert storage._signups[s1.id].amount_owed == 6.0   # unchanged
    assert storage._signups[s2.id].amount_owed == 12.0
    assert storage._signups[s3.id].amount_owed == 12.0


def test_calculate_costs_all_adjusted_summing_to_total_succeeds(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    storage.update_signup(s1.id, SignupUpdate(amount_owed=20.0, amount_adjusted=True))
    storage.update_signup(s2.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 200
    data = response.json()
    assert data["base_amount"] == 0.0


def test_calculate_costs_all_adjusted_not_summing_to_total_errors(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    storage.update_signup(s1.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))
    storage.update_signup(s2.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))  # sum=$20, not $30

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 400
    assert "20.00" in response.json()["detail"]
    assert "30.00" in response.json()["detail"]


def test_calculate_costs_no_confirmed_players_errors(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd signups/backend && .venv/bin/python -m pytest tests/test_calculate_costs.py -v
```

Expected: 4 failures (the logic hasn't changed yet), 1 pass (`test_calculate_costs_no_confirmed_players_errors` and `test_calculate_costs_splits_evenly_with_no_adjusted_players` may pass — that's fine).

---

### Task 2: Implement the updated calculation logic

**Files:**
- Modify: `signups/backend/routers/admin.py` — `calculate_costs` function

- [ ] **Step 1: Replace the `calculate_costs` function body**

Open `signups/backend/routers/admin.py`. Replace lines 90–112 with:

```python
@router.post("/sessions/{session_id}/calculate-costs", response_model=CostCalculationResult)
def calculate_costs(
    session_id: str, storage: StorageAdapter = Depends(get_storage)
) -> CostCalculationResult:
    courts = storage.get_courts(session_id)
    confirmed = [
        signup for signup in storage.get_signups(session_id) if signup.status == SignupStatus.confirmed
    ]
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed players to calculate costs for",
        )
    total_cost = sum(court.total_cost for court in courts)

    adjusted = [s for s in confirmed if s.amount_adjusted and s.amount_owed is not None]
    unadjusted = [s for s in confirmed if not s.amount_adjusted]
    adjusted_total = sum(s.amount_owed for s in adjusted)

    if not unadjusted:
        if round(adjusted_total, 2) != round(total_cost, 2):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjusted amounts (${adjusted_total:.2f}) do not sum to total cost (${total_cost:.2f})",
            )
        return CostCalculationResult(total_cost=total_cost, confirmed_count=len(confirmed), base_amount=0.0)

    remaining = total_cost - adjusted_total
    base_amount = round(remaining / len(unadjusted), 2)
    for signup in unadjusted:
        storage.update_signup(signup.id, SignupUpdate(amount_owed=base_amount))
    return CostCalculationResult(
        total_cost=total_cost,
        confirmed_count=len(confirmed),
        base_amount=base_amount,
    )
```

- [ ] **Step 2: Run all tests and verify they pass**

```bash
cd signups/backend && .venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass including the 5 new ones.

- [ ] **Step 3: Commit**

```bash
git add signups/backend/routers/admin.py signups/backend/tests/test_calculate_costs.py
git commit -m "feat: split remaining cost among unadjusted players after manual adjustments"
```
