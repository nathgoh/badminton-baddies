from analyses.evidence import build_shuttle_metrics
from schemas import ShotSelectionMetrics, ShuttleSample


def test_build_shuttle_metrics_prefers_observed_samples() -> None:
    shot_selection = ShotSelectionMetrics(
        overview="",
        events=[],
    )
    observed = [
        ShuttleSample(timestamp_seconds=1.0, x=0.48, y=0.22, confidence=0.91, source="observed"),
        ShuttleSample(timestamp_seconds=1.2, x=0.51, y=0.27, confidence=0.88, source="observed"),
    ]

    metrics = build_shuttle_metrics(
        shot_selection,
        tracking_summary=None,
        observed_samples=observed,
    )

    assert metrics.samples[:2] == observed
    assert "directly observed" in metrics.uncertainty_note.lower()


def test_gaussian_shuttle_detector_rejects_large_player_blobs() -> None:
    from pipelines.cv.shuttle import score_shuttle_candidate

    small_fast = score_shuttle_candidate(area_px=18, speed_px=24, distance_to_track_px=32)
    large_blob = score_shuttle_candidate(area_px=340, speed_px=24, distance_to_track_px=32)

    assert small_fast > large_blob


def test_gaussian_shuttle_detector_prefers_candidates_closer_to_the_player() -> None:
    from pipelines.cv.shuttle import score_shuttle_candidate

    nearby = score_shuttle_candidate(area_px=18, speed_px=24, distance_to_track_px=12)
    far_away = score_shuttle_candidate(area_px=18, speed_px=24, distance_to_track_px=120)

    assert nearby > far_away
