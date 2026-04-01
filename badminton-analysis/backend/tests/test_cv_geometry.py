import cv2
import numpy as np
import pytest

from pipelines.cv.geometry import (
    build_court_homography,
    summarize_projected_track,
)
from schemas import CourtModel, CourtPoint, MatchType, TrackSample


def test_summarize_projected_track_uses_court_meters_not_image_norms() -> None:
    court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.9, y=0.1),
            CourtPoint(x=0.9, y=0.9),
            CourtPoint(x=0.1, y=0.9),
        ],
    )
    samples = [
        TrackSample(frame_index=0, timestamp_seconds=0.0, x=0.25, y=0.75),
        TrackSample(frame_index=1, timestamp_seconds=0.2, x=0.25, y=0.55),
        TrackSample(frame_index=2, timestamp_seconds=0.4, x=0.25, y=0.35),
    ]

    homography = build_court_homography(court, MatchType.MENS_SINGLES)
    summary = summarize_projected_track(samples, homography)

    assert summary.total_distance_meters == pytest.approx(6.7, abs=0.15)


def test_build_court_homography_normalizes_reordered_points() -> None:
    ordered_court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.9, y=0.1),
            CourtPoint(x=0.9, y=0.9),
            CourtPoint(x=0.1, y=0.9),
        ],
    )
    shuffled_court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.9, y=0.9),
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.1, y=0.9),
            CourtPoint(x=0.9, y=0.1),
        ],
    )
    source_corners = np.array(
        [
            [[0.1, 0.1]],
            [[0.9, 0.1]],
            [[0.9, 0.9]],
            [[0.1, 0.9]],
        ],
        dtype=np.float32,
    )
    expected_corners = [
        (0.0, 0.0),
        (5.18, 0.0),
        (5.18, 13.4),
        (0.0, 13.4),
    ]

    ordered_projection = cv2.perspectiveTransform(
        source_corners, build_court_homography(ordered_court, MatchType.MENS_SINGLES).matrix
    )[:, 0, :]
    shuffled_projection = cv2.perspectiveTransform(
        source_corners, build_court_homography(shuffled_court, MatchType.MENS_SINGLES).matrix
    )[:, 0, :]

    for projected in (ordered_projection, shuffled_projection):
        for actual, expected in zip(projected, expected_corners, strict=False):
            assert actual[0] == pytest.approx(expected[0], abs=1e-3)
            assert actual[1] == pytest.approx(expected[1], abs=1e-3)


def test_build_court_homography_rejects_degenerate_points() -> None:
    court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.3, y=0.3),
            CourtPoint(x=0.5, y=0.5),
            CourtPoint(x=0.7, y=0.7),
        ],
    )

    with pytest.raises(ValueError, match="convex|degenerate"):
        build_court_homography(court, MatchType.MENS_SINGLES)


def test_summarize_projected_track_ignores_off_court_samples() -> None:
    court = CourtModel(
        confidence=0.9,
        adjustment_hint="",
        points=[
            CourtPoint(x=0.1, y=0.1),
            CourtPoint(x=0.9, y=0.1),
            CourtPoint(x=0.9, y=0.9),
            CourtPoint(x=0.1, y=0.9),
        ],
    )
    in_bounds_samples = [
        TrackSample(frame_index=0, timestamp_seconds=0.0, x=0.25, y=0.75),
        TrackSample(frame_index=2, timestamp_seconds=0.4, x=0.25, y=0.35),
    ]
    with_off_court_samples = [
        TrackSample(frame_index=0, timestamp_seconds=0.0, x=0.25, y=0.75),
        TrackSample(frame_index=1, timestamp_seconds=0.2, x=0.98, y=0.55),
        TrackSample(frame_index=2, timestamp_seconds=0.4, x=0.25, y=0.35),
    ]

    homography = build_court_homography(court, MatchType.MENS_SINGLES)
    clean_summary = summarize_projected_track(in_bounds_samples, homography)
    filtered_summary = summarize_projected_track(with_off_court_samples, homography)

    assert filtered_summary.total_distance_meters == pytest.approx(
        clean_summary.total_distance_meters
    )


def test_selected_player_focus_lock_prefers_high_iou_track() -> None:
    from pipelines.cv.geometry import select_focused_track_id
    from schemas import DetectionBox, PlayerCandidate, PlayerTrackSummary

    selected_player = PlayerCandidate(
        player_id="detected-player-1",
        label="Detected Player A",
        side="near",
        focus_hint="Selected",
        bounding_box=DetectionBox(x=0.18, y=0.56, width=0.12, height=0.23),
    )
    track_a = PlayerTrackSummary(
        track_id="track-7",
        source_player_id=None,
        total_distance_meters=0.0,
        recovery_score=0,
        court_coverage_percent=0,
        change_of_direction_count=0,
        burst_count=0,
        directional_balance={"left": 0.5, "right": 0.5},
        zone_occupancy={"front": 0, "mid": 100, "rear": 0},
        heatmap=[],
        samples=[],
    )
    track_b = track_a.model_copy(update={"track_id": "track-11"})

    first_boxes = {
        "track-7": DetectionBox(x=0.19, y=0.57, width=0.12, height=0.22),
        "track-11": DetectionBox(x=0.62, y=0.31, width=0.1, height=0.2),
    }

    assert select_focused_track_id(selected_player, [track_a, track_b], first_boxes) == "track-7"


def test_selected_player_focus_lock_fails_closed_without_overlap() -> None:
    from pipelines.cv.geometry import select_focused_track_id
    from schemas import DetectionBox, PlayerCandidate, PlayerTrackSummary

    selected_player = PlayerCandidate(
        player_id="detected-player-1",
        label="Detected Player A",
        side="near",
        focus_hint="Selected",
        bounding_box=DetectionBox(x=0.18, y=0.56, width=0.12, height=0.23),
    )
    track = PlayerTrackSummary(
        track_id="track-7",
        source_player_id=None,
        total_distance_meters=0.0,
        recovery_score=0,
        court_coverage_percent=0,
        change_of_direction_count=0,
        burst_count=0,
        directional_balance={"left": 0.5, "right": 0.5},
        zone_occupancy={"front": 0, "mid": 100, "rear": 0},
        heatmap=[],
        samples=[],
    )

    first_boxes = {
        "track-7": DetectionBox(x=0.72, y=0.18, width=0.1, height=0.2),
    }

    assert select_focused_track_id(selected_player, [track], first_boxes) is None
