from datetime import date, timedelta

from ..models import PlayerUpsert


def _setup(client):
    session_response = client.post(
        "/api/sessions",
        json={
            "name": "Test",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "is_active": True,
            "cancel_window_hours": 48,
        },
    )
    session = session_response.json()
    session_id = session["id"]
    client.post(
        f"/api/sessions/{session_id}/courts",
        json={
            "name": "Court A",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_players": 2,
            "total_cost": 20.0,
        },
    )
    client.post(
        f"/api/sessions/{session_id}/courts",
        json={
            "name": "Court B",
            "start_time": "19:00",
            "end_time": "21:00",
            "max_players": 2,
            "total_cost": 10.0,
        },
    )
    return session


def _signup(client, token, email, name):
    return client.post(
        f"/api/public/{token}/signup",
        json={
            "email": email,
            "name": name,
            "venmo_or_phone": "@x",
            "payment_agreed": True,
        },
    )


def test_get_admin_session(client):
    session = _setup(client)

    response = client.get(f"/api/admin/sessions/{session['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["session"]["id"] == session["id"]
    assert data["total_cost"] == 30.0
    assert data["total_capacity"] == 4


def test_calculate_costs(client):
    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")

    response = client.post(f"/api/admin/sessions/{session['id']}/calculate-costs")

    assert response.status_code == 200
    data = response.json()
    assert data["base_amount"] == 15.0
    assert data["confirmed_count"] == 2


def test_calculate_costs_skips_adjusted(client):
    session = _setup(client)
    token = session["access_token"]
    signup_a = _signup(client, token, "a@t.com", "Alice").json()
    _signup(client, token, "b@t.com", "Bob")
    client.patch(
        f"/api/admin/signups/{signup_a['id']}",
        json={"amount_owed": 5.0, "amount_adjusted": True},
    )

    client.post(f"/api/admin/sessions/{session['id']}/calculate-costs")
    response = client.get(f"/api/admin/sessions/{session['id']}")

    signups = response.json()["signups"]
    alice = next(signup for signup in signups if signup["email"] == "a@t.com")
    assert alice["amount_owed"] == 5.0
    assert alice["amount_adjusted"] is True


def test_confirmed_signup_recalculates_costs(client):
    session = _setup(client)
    token = session["access_token"]

    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")

    response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = response.json()["signups"]

    assert response.status_code == 200
    assert {signup["email"]: signup["amount_owed"] for signup in signups} == {
        "a@t.com": 15.0,
        "b@t.com": 15.0,
    }


def test_promote_from_waitlist(client):
    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")
    waitlist_signup = _signup(client, token, "e@t.com", "Eve").json()

    assert waitlist_signup["status"] == "waitlist"

    response = client.post(f"/api/admin/signups/{waitlist_signup['id']}/promote")

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_admin_cancel_signup(client):
    session = _setup(client)
    signup = _signup(client, session["access_token"], "a@t.com", "Alice").json()

    response = client.delete(f"/api/admin/signups/{signup['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_regenerate_token(client):
    session = _setup(client)
    old_token = session["access_token"]

    response = client.post(f"/api/admin/sessions/{session['id']}/regenerate-token")

    assert response.status_code == 200
    new_token = response.json()["access_token"]
    assert new_token != old_token
    assert client.get(f"/api/public/{old_token}").status_code == 404
    assert client.get(f"/api/public/{new_token}").status_code == 200


def test_list_players(client, storage):
    storage.upsert_player(PlayerUpsert(email="a@t.com", name="Alice", venmo_or_phone="@alice"))

    response = client.get("/api/admin/players")

    assert response.status_code == 200
    assert len(response.json()) == 1


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


def test_waitlist_signup_does_not_recalculate_costs(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")

    response = client.post(f"/api/admin/sessions/{session['id']}/calculate-costs")
    assert response.status_code == 200
    assert response.json()["base_amount"] == 7.5

    before_waitlist = client.get(f"/api/admin/sessions/{session['id']}")
    expected_amounts = {
        signup["email"]: signup["amount_owed"]
        for signup in before_waitlist.json()["signups"]
        if signup["status"] == "confirmed"
    }
    assert expected_amounts == {
        "a@t.com": 7.5,
        "b@t.com": 7.5,
        "c@t.com": 7.5,
        "d@t.com": 7.5,
    }

    call_count = 0
    original_calculate_costs = admin_router.calculate_costs

    def counting_calculate_costs(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_calculate_costs(*args, **kwargs)

    monkeypatch.setattr(admin_router, "calculate_costs", counting_calculate_costs)

    response = _signup(client, token, "e@t.com", "Eve")

    assert response.status_code == 201
    assert response.json()["status"] == "waitlist"
    assert call_count == 0

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["e@t.com"]["amount_owed"] is None
    assert {email: signups[email]["amount_owed"] for email in expected_amounts} == expected_amounts


def test_manual_amount_edit_recalculates_remaining_confirmed_players(client):
    session = _setup(client)
    token = session["access_token"]
    alice = _signup(client, token, "a@t.com", "Alice").json()
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")

    response = client.patch(
        f"/api/admin/signups/{alice['id']}",
        json={"amount_owed": 6.0, "amount_adjusted": True},
    )

    assert response.status_code == 200

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["a@t.com"]["amount_owed"] == 6.0
    assert signups["a@t.com"]["amount_adjusted"] is True
    assert signups["b@t.com"]["amount_owed"] == 12.0
    assert signups["c@t.com"]["amount_owed"] == 12.0


def test_waitlist_cancel_does_not_recalculate_costs(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")

    response = client.post(f"/api/admin/sessions/{session['id']}/calculate-costs")
    assert response.status_code == 200
    assert response.json()["base_amount"] == 7.5

    before_waitlist = client.get(f"/api/admin/sessions/{session['id']}")
    expected_amounts = {
        signup["email"]: signup["amount_owed"]
        for signup in before_waitlist.json()["signups"]
        if signup["status"] == "confirmed"
    }
    assert expected_amounts == {
        "a@t.com": 7.5,
        "b@t.com": 7.5,
        "c@t.com": 7.5,
        "d@t.com": 7.5,
    }

    eve = _signup(client, token, "e@t.com", "Eve").json()

    call_count = 0
    original_calculate_costs = admin_router.calculate_costs

    def counting_calculate_costs(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_calculate_costs(*args, **kwargs)

    monkeypatch.setattr(admin_router, "calculate_costs", counting_calculate_costs)

    response = client.delete(f"/api/admin/signups/{eve['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert call_count == 0

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert "e@t.com" not in signups
    assert {email: signups[email]["amount_owed"] for email in expected_amounts} == expected_amounts


def test_admin_cancel_with_waitlist_promotion_recalculates_once_for_final_roster(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    bob = _signup(client, token, "b@t.com", "Bob").json()
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")
    _signup(client, token, "e@t.com", "Eve")

    baseline = client.post(f"/api/admin/sessions/{session['id']}/calculate-costs")
    assert baseline.status_code == 200
    assert baseline.json()["base_amount"] == 7.5

    call_count = 0
    original_calculate_costs = admin_router.calculate_costs

    def counting_calculate_costs(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_calculate_costs(*args, **kwargs)

    monkeypatch.setattr(admin_router, "calculate_costs", counting_calculate_costs)

    response = client.delete(f"/api/admin/signups/{bob['id']}")

    assert response.status_code == 200
    assert call_count == 1

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["e@t.com"]["status"] == "confirmed"
    assert signups["a@t.com"]["amount_owed"] == 7.5
    assert signups["c@t.com"]["amount_owed"] == 7.5
    assert signups["d@t.com"]["amount_owed"] == 7.5
    assert signups["e@t.com"]["amount_owed"] == 7.5
