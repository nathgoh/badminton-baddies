from datetime import date, timedelta


def _make_session(client, is_active=True, cancel_window_hours=48):
    response = client.post(
        "/api/sessions",
        json={
            "name": "Test Session",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "is_active": is_active,
            "cancel_window_hours": cancel_window_hours,
        },
    )
    session = response.json()
    client.post(
        f"/api/sessions/{session['id']}/courts",
        json={
            "name": "Doubles",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_players": 2,
            "total_cost": 20.0,
        },
    )
    return session


def _signup(client, token, email="a@test.com", name="Alice"):
    return client.post(
        f"/api/public/{token}/signup",
        json={
            "email": email,
            "name": name,
            "venmo_or_phone": "@alice",
            "payment_agreed": True,
        },
    )


def test_get_public_session(client):
    session = _make_session(client)

    response = client.get(f"/api/public/{session['access_token']}")

    assert response.status_code == 200
    data = response.json()
    assert data["session"]["id"] == session["id"]
    assert data["signups"] == []
    assert data["confirmed_count"] == 0
    assert data["total_capacity"] == 2


def test_get_public_session_includes_active_signup_list(client):
    session = _make_session(client)
    token = session["access_token"]
    _signup(client, token, email="a@test.com", name="Alice")
    _signup(client, token, email="b@test.com", name="Bob")

    response = client.get(f"/api/public/{token}")

    assert response.status_code == 200
    names = [signup["name"] for signup in response.json()["signups"]]
    assert names == ["Alice", "Bob"]


def test_get_public_session_invalid_token(client):
    response = client.get("/api/public/badtoken")

    assert response.status_code == 404


def test_signup_confirmed(client):
    session = _make_session(client)

    response = _signup(client, session["access_token"])

    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"


def test_signup_goes_to_waitlist_when_full(client):
    session = _make_session(client)
    token = session["access_token"]
    _signup(client, token, email="a@test.com", name="Alice")
    _signup(client, token, email="b@test.com", name="Bob")

    response = _signup(client, token, email="c@test.com", name="Carol")

    assert response.status_code == 201
    assert response.json()["status"] == "waitlist"


def test_duplicate_signup_rejected(client):
    session = _make_session(client)
    token = session["access_token"]
    _signup(client, token, email="a@test.com")

    response = _signup(client, token, email="a@test.com")

    assert response.status_code == 409


def test_signup_closed_session(client):
    session = _make_session(client, is_active=False)

    response = _signup(client, session["access_token"])

    assert response.status_code == 400


def test_player_lookup_autofill(client):
    session = _make_session(client)
    token = session["access_token"]
    _signup(client, token, email="a@test.com", name="Alice")

    response = client.get(f"/api/public/{token}/player-lookup?email=a@test.com")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
    assert response.json()["venmo_or_phone"] == "@alice"


def test_player_lookup_unknown_email(client):
    session = _make_session(client)

    response = client.get(f"/api/public/{session['access_token']}/player-lookup?email=unknown@test.com")

    assert response.status_code == 404


def test_cancel_lookup_within_window(client):
    session = _make_session(client, cancel_window_hours=48)
    token = session["access_token"]
    _signup(client, token, email="a@test.com")

    response = client.get(f"/api/public/{token}/cancel-lookup?email=a@test.com")

    assert response.status_code == 200
    data = response.json()
    assert data["can_cancel"] is True


def test_cancel_self(client):
    session = _make_session(client)
    token = session["access_token"]
    signup_response = _signup(client, token, email="a@test.com")
    signup_id = signup_response.json()["id"]

    response = client.post(
        f"/api/public/{token}/cancel",
        json={"signup_id": signup_id, "email": "a@test.com"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_wrong_email_rejected(client):
    session = _make_session(client)
    token = session["access_token"]
    signup_response = _signup(client, token, email="a@test.com")
    signup_id = signup_response.json()["id"]

    response = client.post(
        f"/api/public/{token}/cancel",
        json={"signup_id": signup_id, "email": "wrong@test.com"},
    )

    assert response.status_code == 403
