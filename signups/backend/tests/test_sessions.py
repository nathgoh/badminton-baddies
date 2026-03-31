def _create_session(client, *, is_active=False):
    response = client.post(
        "/api/sessions",
        json={"name": "S1", "date": "2026-04-01", "is_active": is_active},
    )
    return response.json()


def _create_court(client, session_id, *, total_cost=20.0, max_players=4):
    response = client.post(
        f"/api/sessions/{session_id}/courts",
        json={
            "name": "Court A",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_players": max_players,
            "total_cost": total_cost,
        },
    )
    return response


def _signup(client, token, email, name):
    response = client.post(
        f"/api/public/{token}/signup",
        json={
            "email": email,
            "name": name,
            "venmo_or_phone": "@x",
            "payment_agreed": True,
        },
    )
    return response


def _amounts_by_email(client, session_id):
    response = client.get(f"/api/admin/sessions/{session_id}")
    return {
        signup["email"]: signup["amount_owed"]
        for signup in response.json()["signups"]
        if signup["status"] == "confirmed"
    }


def test_list_sessions_empty(client):
    response = client.get("/api/sessions")

    assert response.status_code == 200
    assert response.json() == []


def test_create_session(client):
    response = client.post(
        "/api/sessions",
        json={
            "name": "HBB Wednesday 3/25/26",
            "date": "2026-03-25",
            "is_active": True,
            "cancel_window_hours": 48,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "HBB Wednesday 3/25/26"
    assert "id" in data
    assert "access_token" in data


def test_create_session_defaults(client):
    response = client.post(
        "/api/sessions",
        json={
            "name": "Test Session",
            "date": "2026-04-01",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_active"] is False
    assert data["cancel_window_hours"] == 48


def test_update_session(client):
    create_response = client.post("/api/sessions", json={"name": "Old Name", "date": "2026-03-25"})
    session_id = create_response.json()["id"]

    response = client.patch(f"/api/sessions/{session_id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_session(client):
    create_response = client.post("/api/sessions", json={"name": "To Delete", "date": "2026-03-25"})
    session_id = create_response.json()["id"]

    response = client.delete(f"/api/sessions/{session_id}")

    assert response.status_code == 204
    list_response = client.get("/api/sessions")
    assert list_response.json() == []


def test_delete_session_removes_courts(client):
    session_id = client.post("/api/sessions", json={"name": "S", "date": "2026-03-25"}).json()["id"]
    client.post(
        f"/api/sessions/{session_id}/courts",
        json={"name": "Court A", "start_time": "19:00", "end_time": "22:00", "max_players": 10, "total_cost": 100.0},
    )

    client.delete(f"/api/sessions/{session_id}")

    admin_response = client.get(f"/api/admin/sessions/{session_id}")
    assert admin_response.status_code == 404


def test_delete_session_removes_signups(client, storage):
    session_id = client.post("/api/sessions", json={"name": "S", "date": "2026-03-25"}).json()["id"]
    token = client.get("/api/sessions").json()[0]["access_token"]
    client.post(
        f"/api/public/{token}/signup",
        json={"email": "a@b.com", "name": "Alice", "venmo_or_phone": "555", "payment_agreed": True},
    )

    client.delete(f"/api/sessions/{session_id}")

    assert storage.get_signups(session_id) == []


def test_create_court(client):
    session_id = _create_session(client)["id"]

    response = _create_court(client, session_id, total_cost=150.0, max_players=18)

    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session_id
    assert data["name"] == "Court A"


def test_delete_court(client):
    session_id = _create_session(client)["id"]
    court_response = _create_court(client, session_id, total_cost=100.0, max_players=10)
    court_id = court_response.json()["id"]

    response = client.delete(f"/api/courts/{court_id}")

    assert response.status_code == 204


def test_create_court_recalculates_costs_for_confirmed_signups(client):
    session = _create_session(client, is_active=True)
    session_id = session["id"]
    token = session["access_token"]
    _create_court(client, session_id, total_cost=20.0, max_players=4)
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")

    response = _create_court(client, session_id, total_cost=10.0, max_players=2)

    assert response.status_code == 201
    assert _amounts_by_email(client, session_id) == {
        "a@t.com": 15.0,
        "b@t.com": 15.0,
    }


def test_update_court_recalculates_costs_for_confirmed_signups(client):
    session = _create_session(client, is_active=True)
    session_id = session["id"]
    token = session["access_token"]
    court_id = _create_court(client, session_id, total_cost=20.0, max_players=4).json()["id"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")

    response = client.patch(f"/api/courts/{court_id}", json={"total_cost": 30.0})

    assert response.status_code == 200
    assert _amounts_by_email(client, session_id) == {
        "a@t.com": 15.0,
        "b@t.com": 15.0,
    }


def test_delete_court_recalculates_costs_for_confirmed_signups(client):
    session = _create_session(client, is_active=True)
    session_id = session["id"]
    token = session["access_token"]
    _create_court(client, session_id, total_cost=20.0, max_players=4)
    extra_court_id = _create_court(client, session_id, total_cost=10.0, max_players=2).json()["id"]
    _signup(client, token, "a@t.com", "Alice")
    _signup(client, token, "b@t.com", "Bob")

    response = client.delete(f"/api/courts/{extra_court_id}")

    assert response.status_code == 204
    assert _amounts_by_email(client, session_id) == {
        "a@t.com": 10.0,
        "b@t.com": 10.0,
    }


def test_update_court_does_not_persist_when_recalculation_would_fail(client):
    session = _create_session(client, is_active=True)
    session_id = session["id"]
    token = session["access_token"]
    court_id = _create_court(client, session_id, total_cost=20.0, max_players=4).json()["id"]
    _create_court(client, session_id, total_cost=10.0, max_players=2)
    alice = _signup(client, token, "a@t.com", "Alice").json()
    bob = _signup(client, token, "b@t.com", "Bob").json()

    response_a = client.patch(
        f"/api/admin/signups/{alice['id']}",
        json={"amount_owed": 20.0, "amount_adjusted": True},
    )
    response_b = client.patch(
        f"/api/admin/signups/{bob['id']}",
        json={"amount_owed": 10.0, "amount_adjusted": True},
    )
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    response = client.patch(f"/api/courts/{court_id}", json={"total_cost": 5.0})

    assert response.status_code == 400
    admin_response = client.get(f"/api/admin/sessions/{session_id}")
    assert admin_response.json()["total_cost"] == 30.0
    assert _amounts_by_email(client, session_id) == {
        "a@t.com": 20.0,
        "b@t.com": 10.0,
    }


def test_delete_court_does_not_persist_when_recalculation_would_fail(client):
    session = _create_session(client, is_active=True)
    session_id = session["id"]
    token = session["access_token"]
    _create_court(client, session_id, total_cost=20.0, max_players=4)
    extra_court_id = _create_court(client, session_id, total_cost=10.0, max_players=2).json()["id"]
    alice = _signup(client, token, "a@t.com", "Alice").json()
    bob = _signup(client, token, "b@t.com", "Bob").json()

    response_a = client.patch(
        f"/api/admin/signups/{alice['id']}",
        json={"amount_owed": 20.0, "amount_adjusted": True},
    )
    response_b = client.patch(
        f"/api/admin/signups/{bob['id']}",
        json={"amount_owed": 10.0, "amount_adjusted": True},
    )
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    response = client.delete(f"/api/courts/{extra_court_id}")

    assert response.status_code == 400
    admin_response = client.get(f"/api/admin/sessions/{session_id}")
    assert admin_response.json()["total_cost"] == 30.0
    assert len(admin_response.json()["courts"]) == 2
    assert _amounts_by_email(client, session_id) == {
        "a@t.com": 20.0,
        "b@t.com": 10.0,
    }


def test_create_court_with_no_confirmed_signups_does_not_error(client):
    session_id = _create_session(client, is_active=True)["id"]

    response = _create_court(client, session_id, total_cost=20.0, max_players=4)

    assert response.status_code == 201
