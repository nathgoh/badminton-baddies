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


def test_calculate_costs_assigns_rounding_remainder_without_losing_total(client: TestClient, storage: InMemoryAdapter):
    session = storage.create_session(SessionCreate(name="Test", date=date.today(), is_active=True))
    storage.create_court(
        CourtCreate(
            session_id=session.id,
            name="Court 1",
            start_time="19:00",
            end_time="22:00",
            max_players=6,
            total_cost=10.0,
        )
    )
    s1 = storage.create_signup(SignupCreate(session_id=session.id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session.id, email="b@x.com", name="B", payment_agreed=True))
    s3 = storage.create_signup(SignupCreate(session_id=session.id, email="c@x.com", name="C", payment_agreed=True))

    response = client.post(f"/api/admin/sessions/{session.id}/calculate-costs")

    assert response.status_code == 200
    amounts = sorted(storage._signups[signup_id].amount_owed for signup_id in [s1.id, s2.id, s3.id])
    assert amounts == [3.33, 3.33, 3.34]
    assert round(sum(amounts), 2) == 10.0


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


def test_calculate_costs_all_adjusted_below_total_succeeds(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    storage.update_signup(s1.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))
    storage.update_signup(s2.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 200
    assert response.json()["base_amount"] == 0.0
    assert storage._signups[s1.id].amount_owed == 10.0
    assert storage._signups[s2.id].amount_owed == 10.0


def test_calculate_costs_all_adjusted_valid_total_leaves_existing_amounts_unchanged(
    client: TestClient, storage: InMemoryAdapter
):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    storage.update_signup(s1.id, SignupUpdate(amount_owed=20.0, amount_adjusted=True))
    storage.update_signup(s2.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 200
    assert response.json()["base_amount"] == 0.0
    assert storage._signups[s1.id].amount_owed == 20.0
    assert storage._signups[s2.id].amount_owed == 10.0


def test_calculate_costs_rejects_adjusted_total_above_session_total(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)  # $30 total
    s1 = storage.create_signup(SignupCreate(session_id=session_id, email="a@x.com", name="A", payment_agreed=True))
    s2 = storage.create_signup(SignupCreate(session_id=session_id, email="b@x.com", name="B", payment_agreed=True))
    storage.update_signup(s1.id, SignupUpdate(amount_owed=25.0, amount_adjusted=True))
    storage.update_signup(s2.id, SignupUpdate(amount_owed=10.0, amount_adjusted=True))
    before = {
        s1.id: storage._signups[s1.id].amount_owed,
        s2.id: storage._signups[s2.id].amount_owed,
    }

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 400
    assert storage._signups[s1.id].amount_owed == before[s1.id]
    assert storage._signups[s2.id].amount_owed == before[s2.id]


def test_calculate_costs_no_confirmed_players_errors(client: TestClient, storage: InMemoryAdapter):
    session_id = _setup(storage)

    response = client.post(f"/api/admin/sessions/{session_id}/calculate-costs")

    assert response.status_code == 400
