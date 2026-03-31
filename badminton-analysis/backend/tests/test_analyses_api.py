import sys
from base64 import b64decode
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import badminton_analysis_api.main as main_module
from badminton_analysis_api.coach_feedback import PydanticAICoachFeedbackEngine
from badminton_analysis_api.models import (
    CoachView,
    CourtModel,
    CourtPoint,
    MatchType,
    PlayerCandidate,
)
from badminton_analysis_api.service import AnalysisService
from badminton_analysis_api.store import AnalysisStore


class FailingCoachFeedbackEngine:
    def create_feedback(self, **_: object) -> None:
        raise RuntimeError("coach engine unavailable")


class FailingPipelineAnalysisService(AnalysisService):
    def _build_analytics(self, match_type: MatchType):  # type: ignore[override]
        raise RuntimeError(f"pipeline exploded for {match_type.value}")


class FakeMediaArtifactPipeline:
    def __init__(self, root: Path) -> None:
        self._root = root

    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> SimpleNamespace:
        analysis_dir = self._root / analysis_id
        analysis_dir.mkdir(parents=True, exist_ok=True)
        video_path = analysis_dir / "source.mp4"
        frame_path = analysis_dir / "setup-frame.png"
        video_path.write_bytes(b"fake-video")
        frame_path.write_bytes(
            b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8B"
                "l0QAAAAASUVORK5CYII="
            )
        )
        return SimpleNamespace(
            source_video_path=str(video_path),
            setup_frame_path=str(frame_path),
            setup_frame_content_type="image/png",
            source_url=str(youtube_url),
        )


class FailingMediaArtifactPipeline:
    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> SimpleNamespace:
        raise RuntimeError(f"unable to prepare media for {youtube_url}")


class FakeCVPipeline:
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SimpleNamespace:
        return SimpleNamespace(
            players=[
                PlayerCandidate(
                    player_id="detected-player-1",
                    label="Detected Player A",
                    side="near",
                    focus_hint="Highest-confidence detected player",
                ),
                PlayerCandidate(
                    player_id="detected-player-2",
                    label="Detected Player B",
                    side="far",
                    focus_hint="Secondary detected player",
                ),
            ],
            court=CourtModel(
                confidence=0.91,
                adjustment_hint="Court lines were fit from the extracted setup frame.",
                points=[
                    CourtPoint(x=0.16, y=0.11),
                    CourtPoint(x=0.84, y=0.11),
                    CourtPoint(x=0.9, y=0.89),
                    CourtPoint(x=0.1, y=0.89),
                ],
            ),
            warnings=[],
        )

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
    ) -> SimpleNamespace:
        tracks = {
            "track-1": SimpleNamespace(
                track_id="track-1",
                source_player_id="detected-player-1",
                total_distance_meters=41.3,
                recovery_score=68,
                court_coverage_percent=76,
                change_of_direction_count=19,
                burst_count=4,
                directional_balance={"left": 0.44, "right": 0.56},
                zone_occupancy={"front": 18, "mid": 47, "rear": 35},
                heatmap=[
                    {"zone": "front-left", "weight": 0.08},
                    {"zone": "mid-centre", "weight": 0.31},
                    {"zone": "rear-right", "weight": 0.09},
                ],
            )
        }
        return SimpleNamespace(
            tracks=tracks,
            warnings=[],
        )

    def extract_pose(self, video_path: str, selected_track_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            sample_count=14,
            warnings=[],
            stance_note="Stance width narrows slightly on late forehand recoveries.",
            preparation_note="Racket preparation starts earlier on balanced interceptions.",
            balance_note="Balance drops when the final recovery hop lands too upright.",
            recovery_note="Recovery timing is playable but still late after deeper exits.",
            stroke_execution_note="Stroke execution quality falls off after off-balance contacts.",
        )


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[TestClient]:
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            media_artifact_pipeline=FakeMediaArtifactPipeline(tmp_path),
            cv_pipeline=FakeCVPipeline(),
        ),
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
    for _ in range(12):
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


def test_create_analysis_prepares_media_and_serves_real_setup_frame(
    client: TestClient,
) -> None:
    analysis_id = _create_analysis(client)

    setup_response = client.get(f"/api/analyses/{analysis_id}/setup")

    assert setup_response.status_code == 200
    setup_payload = setup_response.json()
    assert setup_payload["setup_frame_url"] == f"/api/analyses/{analysis_id}/setup-frame"

    frame_response = client.get(setup_payload["setup_frame_url"])

    assert frame_response.status_code == 200
    assert frame_response.headers["content-type"] == "image/png"
    assert frame_response.content


def test_create_analysis_uses_cv_setup_detection_outputs(client: TestClient) -> None:
    analysis_id = _create_analysis(client, match_type="mens_singles")

    setup_response = client.get(f"/api/analyses/{analysis_id}/setup")

    assert setup_response.status_code == 200
    setup = setup_response.json()
    assert setup["players"][0]["label"] == "Detected Player A"
    assert setup["players"][0]["player_id"] == "detected-player-1"
    assert setup["court"]["confidence"] == 0.91
    assert setup["court"]["adjustment_hint"] == (
        "Court lines were fit from the extracted setup frame."
    )


def test_create_analysis_fails_cleanly_when_media_ingestion_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            media_artifact_pipeline=FailingMediaArtifactPipeline(),
            cv_pipeline=FakeCVPipeline(),
        ),
    )
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/analyses",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=badminton-demo",
                "match_type": "mixed_doubles",
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Unable to prepare media for analysis: "
        "unable to prepare media for https://www.youtube.com/watch?v=badminton-demo"
    )


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
    assert doubles_setup.json()["setup_frame_url"].endswith("/setup-frame")

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


def test_run_analysis_uses_cv_tracking_and_pose_signals_in_analytics(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")

    run_response = client.post(f"/api/analyses/{analysis_id}/run")

    assert run_response.status_code == 202

    _poll_until_terminal(client, analysis_id)
    report = client.get(f"/api/analyses/{analysis_id}/report").json()

    assert report["analytics_view"]["movement"]["total_distance_meters"] == 41.3
    assert report["analytics_view"]["movement"]["recovery_score"] == 68
    assert report["analytics_view"]["movement"]["burst_count"] == 4
    assert report["analytics_view"]["positioning"]["zone_occupancy"]["mid"] == 47
    assert report["analytics_view"]["mechanics"]["stance_note"] == (
        "Stance width narrows slightly on late forehand recoveries."
    )


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
            cv_pipeline=FakeCVPipeline(),
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
        FailingPipelineAnalysisService(
            store=AnalysisStore(),
            cv_pipeline=FakeCVPipeline(),
        ),
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


def test_status_walks_each_mock_pipeline_stage_before_completion(client: TestClient) -> None:
    analysis_id, _ = _ready_analysis(client, match_type="mens_singles")

    run_response = client.post(f"/api/analyses/{analysis_id}/run")

    assert run_response.status_code == 202

    statuses = _poll_until_terminal(client, analysis_id)

    assert [status["message"] for status in statuses[:-1]] == [
        "Ingesting the YouTube match and normalizing the video.",
        "Extracting the setup frame from the opening rally window.",
        "Detecting court geometry and applying any saved manual overrides.",
        "Detecting players and building multi-person tracks.",
        "Assigning the selected player to the tracked movement sequence.",
        "Extracting pose landmarks and movement signals.",
        "Inferring shot events from the tracked rally sequence.",
        "Scoring tactical shot quality and decision outcomes.",
        "Assembling the coach report and analytics evidence.",
    ]
    assert statuses[-1]["stage"] == "completed"
    assert statuses[-1]["message"] == "Report generated successfully."


def test_owner_header_populates_records_and_hides_other_owners(client: TestClient) -> None:
    alex_headers = {"X-Owner-Id": "coach-alex"}
    bianca_headers = {"X-Owner-Id": "coach-bianca"}
    alex_response = client.post(
        "/api/analyses",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=badminton-demo",
            "match_type": "mens_singles",
        },
        headers=alex_headers,
    )
    bianca_response = client.post(
        "/api/analyses",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=badminton-demo-2",
            "match_type": "mixed_doubles",
        },
        headers=bianca_headers,
    )

    assert alex_response.status_code == 201
    assert bianca_response.status_code == 201

    alex_id = alex_response.json()["analysis_id"]
    bianca_id = bianca_response.json()["analysis_id"]

    alex_list = client.get("/api/analyses", headers=alex_headers)
    bianca_list = client.get("/api/analyses", headers=bianca_headers)

    assert alex_list.status_code == 200
    assert bianca_list.status_code == 200
    assert alex_list.json()["total"] == 1
    assert bianca_list.json()["total"] == 1
    assert alex_list.json()["items"][0]["analysis_id"] == alex_id
    assert alex_list.json()["items"][0]["owner_id"] == "coach-alex"
    assert bianca_list.json()["items"][0]["analysis_id"] == bianca_id
    assert bianca_list.json()["items"][0]["owner_id"] == "coach-bianca"

    unauthorized_setup = client.get(f"/api/analyses/{bianca_id}/setup", headers=alex_headers)

    assert unauthorized_setup.status_code == 404
    assert unauthorized_setup.json()["detail"] == "Analysis not found."


def test_pydanticai_engine_can_drive_coach_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgent:
        def __init__(self, model: str, **kwargs: object) -> None:
            assert model == "openai:gpt-5.2"
            assert kwargs["output_type"] is CoachView
            assert "instructions" in kwargs

        def run_sync(self, prompt: str) -> SimpleNamespace:
            assert "confidence_annotations" in prompt
            assert "tracked_player" in prompt
            return SimpleNamespace(
                output=CoachView(
                    summary="AI summary",
                    strengths=["AI strength"],
                    priority_issues=["AI issue"],
                    shot_selection_notes="AI shot notes",
                    footwork_notes="AI footwork notes",
                    positioning_notes="AI positioning notes",
                    confidence_notes="AI confidence notes",
                    recommended_drills=["AI drill"],
                )
            )

    monkeypatch.setitem(sys.modules, "pydantic_ai", SimpleNamespace(Agent=FakeAgent))
    monkeypatch.setattr(
        main_module,
        "service",
        AnalysisService(
            store=AnalysisStore(),
            coach_feedback_engine=PydanticAICoachFeedbackEngine(model="openai:gpt-5.2"),
            cv_pipeline=FakeCVPipeline(),
        ),
    )

    with TestClient(main_module.app) as client:
        analysis_id, _ = _ready_analysis(client)

        run_response = client.post(f"/api/analyses/{analysis_id}/run")
        statuses = _poll_until_terminal(client, analysis_id)
        report_response = client.get(f"/api/analyses/{analysis_id}/report")

    assert run_response.status_code == 202
    assert statuses[-1]["stage"] == "completed"
    assert report_response.status_code == 200
    assert report_response.json()["coach_view"]["summary"] == "AI summary"


def test_pagination_clamps_invalid_page_values(client: TestClient) -> None:
    _create_analysis(client, match_type="mens_singles")

    zero_page = client.get("/api/analyses?page=0&page_size=10")
    negative_page = client.get("/api/analyses?page=-1&page_size=10")

    assert zero_page.status_code == 200
    assert zero_page.json()["page"] == 1
    assert zero_page.json()["total"] == 1
    assert len(zero_page.json()["items"]) == 1

    assert negative_page.status_code == 200
    assert negative_page.json()["page"] == 1


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
