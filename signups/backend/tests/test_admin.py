from datetime import date, timedelta

from ..models import PlayerUpsert, SignupUpdate


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


def test_promote_from_waitlist(client, storage):
    session = _setup(client)
    token = session["access_token"]
    alice = _signup(client, token, "a@t.com", "Alice").json()
    bob = _signup(client, token, "b@t.com", "Bob").json()
    carol = _signup(client, token, "c@t.com", "Carol").json()
    dan = _signup(client, token, "d@t.com", "Dan").json()
    waitlist_signup = _signup(client, token, "e@t.com", "Eve").json()

    assert waitlist_signup["status"] == "waitlist"

    storage.update_signup(alice["id"], SignupUpdate(amount_owed=11.0))
    storage.update_signup(bob["id"], SignupUpdate(amount_owed=12.0))
    storage.update_signup(carol["id"], SignupUpdate(amount_owed=13.0))
    storage.update_signup(dan["id"], SignupUpdate(amount_owed=14.0))

    response = client.post(f"/api/admin/signups/{waitlist_signup['id']}/promote")

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}
    assert {email: signups[email]["amount_owed"] for email in ["a@t.com", "b@t.com", "c@t.com", "d@t.com", "e@t.com"]} == {
        "a@t.com": 6.0,
        "b@t.com": 6.0,
        "c@t.com": 6.0,
        "d@t.com": 6.0,
        "e@t.com": 6.0,
    }


def test_admin_cancel_signup(client, storage):
    session = _setup(client)
    token = session["access_token"]
    signup_a = _signup(client, token, "a@t.com", "Alice").json()
    signup_b = _signup(client, token, "b@t.com", "Bob").json()
    signup_c = _signup(client, token, "c@t.com", "Carol").json()
    signup_d = _signup(client, token, "d@t.com", "Dan").json()

    storage.update_signup(signup_a["id"], SignupUpdate(amount_owed=11.0))
    storage.update_signup(signup_b["id"], SignupUpdate(amount_owed=12.0))
    storage.update_signup(signup_c["id"], SignupUpdate(amount_owed=13.0))
    storage.update_signup(signup_d["id"], SignupUpdate(amount_owed=14.0))

    response = client.delete(f"/api/admin/signups/{signup_a['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}
    assert "a@t.com" not in signups
    assert signups["b@t.com"]["amount_owed"] == 10.0
    assert signups["c@t.com"]["amount_owed"] == 10.0
    assert signups["d@t.com"]["amount_owed"] == 10.0


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


def test_waitlist_signup_does_not_recalculate_costs(client, storage):
    session = _setup(client)
    token = session["access_token"]
    signup_a = _signup(client, token, "a@t.com", "Alice").json()
    signup_b = _signup(client, token, "b@t.com", "Bob").json()
    signup_c = _signup(client, token, "c@t.com", "Carol").json()
    signup_d = _signup(client, token, "d@t.com", "Dan").json()

    storage.update_signup(signup_a["id"], SignupUpdate(amount_owed=11.0))
    storage.update_signup(signup_b["id"], SignupUpdate(amount_owed=12.0))
    storage.update_signup(signup_c["id"], SignupUpdate(amount_owed=13.0))
    storage.update_signup(signup_d["id"], SignupUpdate(amount_owed=14.0))

    before_waitlist = client.get(f"/api/admin/sessions/{session['id']}")
    assert {
        signup["email"]: signup["amount_owed"]
        for signup in before_waitlist.json()["signups"]
        if signup["status"] == "confirmed"
    } == {
        "a@t.com": 11.0,
        "b@t.com": 12.0,
        "c@t.com": 13.0,
        "d@t.com": 14.0,
    }

    response = _signup(client, token, "e@t.com", "Eve")

    assert response.status_code == 201
    assert response.json()["status"] == "waitlist"

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["e@t.com"]["amount_owed"] is None
    assert {
        "a@t.com": signups["a@t.com"]["amount_owed"],
        "b@t.com": signups["b@t.com"]["amount_owed"],
        "c@t.com": signups["c@t.com"]["amount_owed"],
        "d@t.com": signups["d@t.com"]["amount_owed"],
    } == {
        "a@t.com": 11.0,
        "b@t.com": 12.0,
        "c@t.com": 13.0,
        "d@t.com": 14.0,
    }


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


def test_manual_amount_edit_on_waitlist_does_not_recalculate_costs(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")
    eve = _signup(client, token, "e@t.com", "Eve").json()

    helper_calls = 0
    original_recalculate_session_costs = admin_router._recalculate_session_costs

    def counting_recalculate_session_costs(*args, **kwargs):
        nonlocal helper_calls
        helper_calls += 1
        return original_recalculate_session_costs(*args, **kwargs)

    monkeypatch.setattr(
        admin_router,
        "_recalculate_session_costs",
        counting_recalculate_session_costs,
        raising=False,
    )

    response = client.patch(
        f"/api/admin/signups/{eve['id']}",
        json={"amount_owed": 9.0, "amount_adjusted": True},
    )

    assert response.status_code == 200
    assert helper_calls == 0
    assert response.json()["status"] == "waitlist"
    assert response.json()["amount_owed"] == 9.0


def test_waitlist_cancel_does_not_recalculate_costs(client, storage):
    session = _setup(client)
    token = session["access_token"]
    signup_a = _signup(client, token, "a@t.com", "Alice").json()
    signup_b = _signup(client, token, "b@t.com", "Bob").json()
    signup_c = _signup(client, token, "c@t.com", "Carol").json()
    signup_d = _signup(client, token, "d@t.com", "Dan").json()

    storage.update_signup(signup_a["id"], SignupUpdate(amount_owed=11.0))
    storage.update_signup(signup_b["id"], SignupUpdate(amount_owed=12.0))
    storage.update_signup(signup_c["id"], SignupUpdate(amount_owed=13.0))
    storage.update_signup(signup_d["id"], SignupUpdate(amount_owed=14.0))

    eve = _signup(client, token, "e@t.com", "Eve").json()

    response = client.delete(f"/api/admin/signups/{eve['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert "e@t.com" not in signups
    assert {
        "a@t.com": signups["a@t.com"]["amount_owed"],
        "b@t.com": signups["b@t.com"]["amount_owed"],
        "c@t.com": signups["c@t.com"]["amount_owed"],
        "d@t.com": signups["d@t.com"]["amount_owed"],
    } == {
        "a@t.com": 11.0,
        "b@t.com": 12.0,
        "c@t.com": 13.0,
        "d@t.com": 14.0,
    }


def test_admin_cancel_with_waitlist_promotion_recalculates_once_for_final_roster(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    bob = _signup(client, token, "b@t.com", "Bob").json()
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "c@t.com", "Carol")
    _signup(client, token, "d@t.com", "Dan")
    eve = _signup(client, token, "e@t.com", "Eve").json()

    helper_calls = 0
    original_recalculate_session_costs = admin_router._recalculate_session_costs

    def counting_recalculate_session_costs(*args, **kwargs):
        nonlocal helper_calls
        helper_calls += 1
        return original_recalculate_session_costs(*args, **kwargs)

    monkeypatch.setattr(
        admin_router,
        "_recalculate_session_costs",
        counting_recalculate_session_costs,
        raising=False,
    )

    response = client.delete(f"/api/admin/signups/{bob['id']}")

    assert response.status_code == 200
    assert helper_calls == 1

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["e@t.com"]["status"] == "confirmed"
    assert signups["a@t.com"]["amount_owed"] == 7.5
    assert signups["c@t.com"]["amount_owed"] == 7.5
    assert signups["d@t.com"]["amount_owed"] == 7.5
    assert signups["e@t.com"]["amount_owed"] == 7.5


def test_admin_cancel_only_confirmed_signup_succeeds_without_recalculation(client, monkeypatch):
    from ..routers import admin as admin_router

    session = _setup(client)
    token = session["access_token"]
    alice = _signup(client, token, "a@t.com", "Alice").json()

    helper_calls = 0
    original_recalculate_session_costs = admin_router._recalculate_session_costs

    def counting_recalculate_session_costs(*args, **kwargs):
        nonlocal helper_calls
        helper_calls += 1
        return original_recalculate_session_costs(*args, **kwargs)

    monkeypatch.setattr(
        admin_router,
        "_recalculate_session_costs",
        counting_recalculate_session_costs,
        raising=False,
    )

    response = client.delete(f"/api/admin/signups/{alice['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert helper_calls == 0

    session_response = client.get(f"/api/admin/sessions/{session['id']}")

    assert session_response.status_code == 200
    assert session_response.json()["signups"] == []
    assert session_response.json()["confirmed_count"] == 0
    assert session_response.json()["waitlist_count"] == 0


def test_invalid_manual_amount_edit_does_not_persist_attempted_change(client):
    session = _setup(client)
    token = session["access_token"]
    alice = _signup(client, token, "a@t.com", "Alice").json()
    bob = _signup(client, token, "b@t.com", "Bob").json()

    first_update = client.patch(
        f"/api/admin/signups/{alice['id']}",
        json={"amount_owed": 25.0, "amount_adjusted": True},
    )

    assert first_update.status_code == 200

    before_invalid_update = client.get(f"/api/admin/sessions/{session['id']}")
    before_signups = {
        signup["email"]: signup for signup in before_invalid_update.json()["signups"]
    }
    assert before_signups["a@t.com"]["amount_owed"] == 25.0
    assert before_signups["a@t.com"]["amount_adjusted"] is True
    assert before_signups["b@t.com"]["amount_owed"] == 5.0
    assert before_signups["b@t.com"]["amount_adjusted"] is False

    response = client.patch(
        f"/api/admin/signups/{bob['id']}",
        json={"amount_owed": 10.0, "amount_adjusted": True},
    )

    assert response.status_code == 400

    session_response = client.get(f"/api/admin/sessions/{session['id']}")
    signups = {signup["email"]: signup for signup in session_response.json()["signups"]}

    assert signups["a@t.com"]["amount_owed"] == 25.0
    assert signups["a@t.com"]["amount_adjusted"] is True
    assert signups["b@t.com"]["amount_owed"] == 5.0
    assert signups["b@t.com"]["amount_adjusted"] is False
