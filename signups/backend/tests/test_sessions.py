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


def test_create_court(client):
    session_response = client.post("/api/sessions", json={"name": "S1", "date": "2026-03-25"})
    session_id = session_response.json()["id"]

    response = client.post(
        f"/api/sessions/{session_id}/courts",
        json={
            "name": "Doubles Court",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_players": 18,
            "total_cost": 150.0,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session_id
    assert data["name"] == "Doubles Court"


def test_delete_court(client):
    session_response = client.post("/api/sessions", json={"name": "S1", "date": "2026-03-25"})
    session_id = session_response.json()["id"]
    court_response = client.post(
        f"/api/sessions/{session_id}/courts",
        json={
            "name": "Court A",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_players": 10,
            "total_cost": 100.0,
        },
    )
    court_id = court_response.json()["id"]

    response = client.delete(f"/api/courts/{court_id}")

    assert response.status_code == 204
