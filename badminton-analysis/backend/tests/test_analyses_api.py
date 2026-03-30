from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import badminton_analysis_api.main as main_module
from badminton_analysis_api.models import MatchType
from badminton_analysis_api.service import AnalysisService
from badminton_analysis_api.store import AnalysisStore


class FailingCoachFeedbackEngine:
    def create_feedback(self, **_: object) -> None:
        raise RuntimeError("coach engine unavailable")


class FailingPipelineAnalysisService(AnalysisService):
    def _build_analytics(self, match_type: MatchType):  # type: ignore[override]
        raise RuntimeError(f"pipeline exploded for {match_type.value}")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(store=AnalysisStore()),
    )
    with TestClient(main_module.app) as test_client:
        yield test_client


def _create_analysis(
    client: TestClient,
    *,
    match_type: str = "mixed_doubles",
    youtube_url: str = "https://www.youtube.com/watch?v=badminton-demo",
) -> str:
    response = client.post(
        "/api/analyses",
        json={
            "youtube_url": youtube_url,
            "match_type": match_type,
        },
    )
    assert response.status_code == 201
    return response.json()["analysis_id"]


def _ready_analysis(client: TestClient, *, match_type: str = "mixed_doubles") -> tuple[str, dict]:
    analysis_id = _create_analysis(client, match_type=match_type)
    setup_response = client.get(f"/api/analyses/{analysis_id}/setup")
    assert setup_response.status_code == 200
    setup_payload = setup_response.json()

    selection_response = client.post(
        f"/api/analyses/{analysis_id}/selection",
        json={
            "player_id": setup_payload["players"][0]["player_id"],
            "court_points": setup_payload["court"]["points"],
        },
    )
    assert selection_response.status_code == 202
    return analysis_id, setup_payload


def _poll_until_terminal(client: TestClient, analysis_id: str) -> list[dict]:
    statuses: list[dict] = []
    for _ in range(6):
        response = client.get(f"/api/analyses/{analysis_id}/status")
        assert response.status_code == 200
        payload = response.json()
        statuses.append(payload)
        if payload["stage"] in {"completed", "failed"}:
            break
    return statuses


def test_creates_analysis_with_match_type_and_returns_setup_required(client: TestClient) -> None:
    response = client.post(
        "/api/analyses",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=badminton-demo",
            "match_type": "mixed_doubles",
        },
    )

    assert response.status_code == 201
    payload = response.json()

    assert payload["match_type"] == "mixed_doubles"
    assert payload["stage"] == "setup_required"
    assert payload["selection_required"] is True
    assert payload["analysis_id"]


def test_rejects_malformed_youtube_url(client: TestClient) -> None:
    response = client.post(
        "/api/analyses",
        json={
            "youtube_url": "not-a-url",
            "match_type": "mens_singles",
        },
    )

    assert response.status_code == 422
    assert "url" in response.json()["detail"][0]["msg"].lower()


def test_setup_returns_match_type_specific_players_and_accepts_court_override(
    client: TestClient,
) -> None:
    singles_analysis_id = _create_analysis(client, match_type="mens_singles")
    doubles_analysis_id = _create_analysis(client, match_type="mixed_doubles")

    singles_setup = client.get(f"/api/analyses/{singles_analysis_id}/setup")
    doubles_setup = client.get(f"/api/analyses/{doubles_analysis_id}/setup")

    assert singles_setup.status_code == 200
    assert doubles_setup.status_code == 200
    assert len(singles_setup.json()["players"]) == 2
    assert len(doubles_setup.json()["players"]) == 4
    assert doubles_setup.json()["setup_frame_url"].startswith("data:image/svg+xml;base64,")

    updated_points = [
        {"x": 0.12, "y": 0.1},
        {"x": 0.88, "y": 0.1},
        {"x": 0.94, "y": 0.9},
        {"x": 0.06, "y": 0.9},
    ]
    player_id = doubles_setup.json()["players"][-1]["player_id"]
    selection_response = client.post(
        f"/api/analyses/{doubles_analysis_id}/selection",
        json={
            "player_id": player_id,
            "court_points": updated_points,
        },
    )

    assert selection_response.status_code == 202
    assert selection_response.json()["stage"] == "ready_to_run"

    refreshed_setup = client.get(f"/api/analyses/{doubles_analysis_id}/setup")
    assert refreshed_setup.json()["court"]["points"] == updated_points


def test_selection_rejects_unknown_player(client: TestClient) -> None:
    analysis_id = _create_analysis(client)
    setup_response = client.get(f"/api/analyses/{analysis_id}/setup")
    payload = setup_response.json()

    response = client.post(
        f"/api/analyses/{analysis_id}/selection",
        json={
            "player_id": "missing-player",
            "court_points": payload["court"]["points"],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Selected player not found."


def test_run_requires_ready_to_run_stage(client: TestClient) -> None:
    analysis_id = _create_analysis(client)

    response = client.post(f"/api/analyses/{analysis_id}/run")

    assert response.status_code == 409
    assert response.json()["detail"] == "Analysis setup must be saved before running."


def test_status_progresses_to_completed_and_report_matches_revised_schema(
    client: TestClient,
) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")

    run_response = client.post(f"/api/analyses/{analysis_id}/run")

    assert run_response.status_code == 202
    assert run_response.json()["stage"] == "analyzing"

    statuses = _poll_until_terminal(client, analysis_id)

    assert statuses[0]["stage"] == "analyzing"
    assert statuses[-1]["stage"] == "completed"
    assert statuses[-1]["progress_percent"] == 100
    assert statuses[-1]["warnings"] == []
    assert statuses[-1]["error_details"] is None
    assert statuses[0]["progress_percent"] < statuses[-1]["progress_percent"]

    report_response = client.get(f"/api/analyses/{analysis_id}/report")

    assert report_response.status_code == 200
    report = report_response.json()

    assert report["analysis_id"] == analysis_id
    assert report["analytics_view"]["mechanics"]["stance_note"]
    assert report["analytics_view"]["movement"]["burst_count"] > 0
    assert report["analytics_view"]["movement"]["directional_balance"]["left"] > 0
    assert report["analytics_view"]["positioning"]["heatmap"]
    assert report["analytics_view"]["positioning"]["spacing_note"].startswith("Base position")
    assert report["analytics_view"]["shot_selection"]["events"][0]["decision_quality"]
    assert report["analytics_view"]["shot_selection"]["events"][0]["evidence"]
    assert "rationale" not in report["analytics_view"]["shot_selection"]["events"][0]
    assert report["coach_view"]["shot_selection_notes"]
    assert report["coach_view"]["footwork_notes"]
    assert report["coach_view"]["positioning_notes"]
    assert report["coach_view"]["confidence_notes"]
    assert report["confidence_annotations"]


def test_doubles_and_mixed_doubles_use_match_aware_positioning_without_role_advice(
    client: TestClient,
) -> None:
    doubles_analysis_id, _ = _ready_analysis(client, match_type="mens_doubles")
    mixed_analysis_id, _ = _ready_analysis(client, match_type="mixed_doubles")

    client.post(f"/api/analyses/{doubles_analysis_id}/run")
    client.post(f"/api/analyses/{mixed_analysis_id}/run")

    _poll_until_terminal(client, doubles_analysis_id)
    _poll_until_terminal(client, mixed_analysis_id)

    doubles_report = client.get(f"/api/analyses/{doubles_analysis_id}/report").json()
    mixed_report = client.get(f"/api/analyses/{mixed_analysis_id}/report").json()
    mixed_text = " ".join(
        [
            mixed_report["coach_view"]["summary"],
            mixed_report["coach_view"]["shot_selection_notes"],
            mixed_report["coach_view"]["positioning_notes"],
            mixed_report["analytics_view"]["positioning"]["spacing_note"],
        ]
    ).lower()

    assert (
        "partner spacing" in doubles_report["analytics_view"]["positioning"]["spacing_note"].lower()
    )
    assert "front-court woman" not in mixed_text
    assert "rear-court man" not in mixed_text
    assert "girl" not in mixed_text
    assert "boy" not in mixed_text


def test_low_confidence_shot_suppresses_overconfident_recommendation(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="womens_singles")

    client.post(f"/api/analyses/{analysis_id}/run")
    _poll_until_terminal(client, analysis_id)

    report = client.get(f"/api/analyses/{analysis_id}/report").json()
    low_confidence_event = report["analytics_view"]["shot_selection"]["events"][-1]

    assert low_confidence_event["decision_score"] < 50
    assert low_confidence_event["execution_score"] < 60
    assert low_confidence_event["recommendation"] == ""


def test_ai_failure_falls_back_to_placeholder_and_adds_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            coach_feedback_engine=FailingCoachFeedbackEngine(),
        ),
    )
    with TestClient(main_module.app) as client:
        analysis_id, _ = _ready_analysis(client)

        client.post(f"/api/analyses/{analysis_id}/run")
        statuses = _poll_until_terminal(client, analysis_id)
        report_response = client.get(f"/api/analyses/{analysis_id}/report")

    assert statuses[-1]["stage"] == "completed"
    assert statuses[-1]["warnings"] == [
        "Coach feedback fallback applied after coach engine unavailable."
    ]
    assert report_response.status_code == 200
    assert report_response.json()["coach_view"]["summary"]


def test_failed_analysis_sets_error_details_and_status_poll_remains_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "service",
        FailingPipelineAnalysisService(store=AnalysisStore()),
    )
    with TestClient(main_module.app) as client:
        analysis_id, _ = _ready_analysis(client, match_type="mens_doubles")

        run_response = client.post(f"/api/analyses/{analysis_id}/run")
        statuses = _poll_until_terminal(client, analysis_id)
        second_failure_status = client.get(f"/api/analyses/{analysis_id}/status")

    assert run_response.status_code == 202
    assert statuses[-1]["stage"] == "failed"
    assert statuses[-1]["error_details"] == "pipeline exploded for mens_doubles"
    assert second_failure_status.status_code == 200
    assert second_failure_status.json()["stage"] == "failed"


def test_lists_paginated_analyses_and_delete_removes_record(client: TestClient) -> None:
    created_ids = [
        _create_analysis(
            client, match_type="mens_singles", youtube_url=f"https://youtu.be/demo-{i}"
        )
        for i in range(3)
    ]

    page_response = client.get("/api/analyses?page=1&page_size=2")

    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["total"] == 3
    assert page_payload["page"] == 1
    assert page_payload["page_size"] == 2
    assert len(page_payload["items"]) == 2

    delete_response = client.delete(f"/api/analyses/{created_ids[1]}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/analyses/{created_ids[1]}/setup")
    refreshed_page = client.get("/api/analyses")

    assert missing_response.status_code == 404
    assert refreshed_page.json()["total"] == 2
