# Waitlist Auto-Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a confirmed player cancels their spot, automatically promote the earliest waitlisted player to confirmed status.

**Architecture:** Add a private helper `_promote_next_from_waitlist(session_id, storage)` to `routers/signups.py`; call it from both the public cancel endpoint (same file) and the admin cancel endpoint (`routers/admin.py`) by importing it. The helper reads the current confirmed count, compares it to total capacity, and promotes the first waitlisted signup by timestamp if a spot is free.

**Tech Stack:** Python, FastAPI, existing `StorageAdapter` interface (no changes needed)

---

### Task 1: Auto-promote on public cancel

**Files:**
- Modify: `signups/backend/routers/signups.py`
- Test: `signups/backend/tests/test_signups.py`

- [ ] **Step 1: Write the failing test**

Add to `signups/backend/tests/test_signups.py`:

```python
def test_cancel_promotes_from_waitlist(client):
    session = _make_session(client)  # capacity = 2
    token = session["access_token"]
    _signup(client, token, email="a@test.com", name="Alice")
    bob = _signup(client, token, email="b@test.com", name="Bob").json()
    carol = _signup(client, token, email="c@test.com", name="Carol").json()
    assert carol["status"] == "waitlist"

    client.post(
        f"/api/public/{token}/cancel",
        json={"signup_id": bob["id"], "email": "b@test.com"},
    )

    response = client.get(f"/api/public/{token}")
    signups = response.json()["signups"]
    carol_after = next(s for s in signups if s["email"] == "c@test.com")
    assert carol_after["status"] == "confirmed"


def test_cancel_with_no_waitlist_does_not_error(client):
    session = _make_session(client)  # capacity = 2
    token = session["access_token"]
    alice = _signup(client, token, email="a@test.com", name="Alice").json()

    response = client.post(
        f"/api/public/{token}/cancel",
        json={"signup_id": alice["id"], "email": "a@test.com"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd signups/backend && python -m pytest tests/test_signups.py::test_cancel_promotes_from_waitlist tests/test_signups.py::test_cancel_with_no_waitlist_does_not_error -v
```

Expected: both FAIL (no promotion logic exists yet)

- [ ] **Step 3: Add the promotion helper and call it in the public cancel endpoint**

In `signups/backend/routers/signups.py`, add this helper after the existing `_cancellation_cutoff` function:

```python
def _promote_next_from_waitlist(session_id: str, storage: StorageAdapter) -> None:
    courts = storage.get_courts(session_id)
    total_capacity = sum(court.max_players for court in courts)
    signups = storage.get_signups(session_id)
    confirmed_count = sum(1 for s in signups if s.status == SignupStatus.confirmed)
    if confirmed_count < total_capacity:
        waitlisted = sorted(
            [s for s in signups if s.status == SignupStatus.waitlist],
            key=lambda s: s.timestamp,
        )
        if waitlisted:
            storage.update_signup(waitlisted[0].id, SignupUpdate(status=SignupStatus.confirmed))
```

Then update the `cancel_signup` endpoint (currently ends at line 167) to call it:

```python
@router.post("/public/{token}/cancel", response_model=Signup)
def cancel_signup(
    token: str, body: CancelRequest, storage: StorageAdapter = Depends(get_storage)
) -> Signup:
    session = _get_session_or_404(token, storage)
    signup = next((item for item in storage.get_signups(session.id) if item.id == body.signup_id), None)
    if signup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found")
    if signup.email != body.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email does not match this signup")
    if signup.status == SignupStatus.cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup is already cancelled")
    if datetime.now(timezone.utc) >= _cancellation_cutoff(session.date, session.cancel_window_hours):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has closed")

    cancelled = storage.update_signup(
        signup.id,
        SignupUpdate(status=SignupStatus.cancelled, cancelled_at=datetime.now(timezone.utc)),
    )
    _promote_next_from_waitlist(session.id, storage)
    return cancelled
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd signups/backend && python -m pytest tests/test_signups.py::test_cancel_promotes_from_waitlist tests/test_signups.py::test_cancel_with_no_waitlist_does_not_error -v
```

Expected: both PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd signups/backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add signups/backend/routers/signups.py signups/backend/tests/test_signups.py
git commit -m "feat: auto-promote from waitlist on public cancel"
```

---

### Task 2: Auto-promote on admin cancel

**Files:**
- Modify: `signups/backend/routers/admin.py`
- Test: `signups/backend/tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

Add to `signups/backend/tests/test_admin.py`:

```python
def test_admin_cancel_promotes_from_waitlist(client):
    session = _setup(client)  # capacity = 4 (2 courts × 2 players each)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")
    bob_signup = _signup(client, token, "b2@t.com", "Bob2").json()
    dan = _signup(client, token, "d@t.com", "Dan").json()
    assert dan["status"] == "waitlist"

    client.delete(f"/api/admin/signups/{bob_signup['id']}")

    response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = response.json()["signups"]
    dan_after = next(s for s in signups if s["email"] == "d@t.com")
    assert dan_after["status"] == "confirmed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd signups/backend && python -m pytest tests/test_admin.py::test_admin_cancel_promotes_from_waitlist -v
```

Expected: FAIL (no promotion logic in admin cancel yet)

- [ ] **Step 3: Import the helper and update admin cancel**

At the top of `signups/backend/routers/admin.py`, add the import of `_promote_next_from_waitlist`. Find the existing router imports block and add:

```python
try:
    from .signups import _promote_next_from_waitlist
except ImportError:
    from routers.signups import _promote_next_from_waitlist
```

Then update the `cancel_signup` handler in `admin.py` (currently at line 150–158):

```python
@router.delete("/signups/{signup_id}", response_model=Signup)
def cancel_signup(signup_id: str, storage: StorageAdapter = Depends(get_storage)) -> Signup:
    try:
        cancelled = storage.update_signup(
            signup_id,
            SignupUpdate(status=SignupStatus.cancelled, cancelled_at=datetime.now(timezone.utc)),
        )
        _promote_next_from_waitlist(cancelled.session_id, storage)
        return cancelled
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd signups/backend && python -m pytest tests/test_admin.py::test_admin_cancel_promotes_from_waitlist -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd signups/backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add signups/backend/routers/admin.py signups/backend/tests/test_admin.py
git commit -m "feat: auto-promote from waitlist on admin cancel"
```
