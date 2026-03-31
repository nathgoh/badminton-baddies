from __future__ import annotations

from math import exp

from schemas import (
    AIRationale,
    AnalysisEvidence,
    AnalyticsView,
    HeatmapCell,
    PlayerTrackSummary,
    PoseSummary,
    PressureWindow,
    ShotSelectionEvent,
    ShotSelectionMetrics,
    ShuttleMetrics,
    ShuttleSample,
)

ZONE_CENTERS: dict[str, tuple[float, float]] = {
    "front-left": (0.2, 0.18),
    "front-centre": (0.5, 0.18),
    "front-right": (0.8, 0.18),
    "mid-left": (0.2, 0.5),
    "mid-centre": (0.5, 0.5),
    "mid-right": (0.8, 0.5),
    "rear-left": (0.2, 0.82),
    "rear-centre": (0.5, 0.82),
    "rear-right": (0.8, 0.82),
}
GAUSSIAN_SIGMA = 0.24


def _parse_timestamp(value: str) -> float:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes * 60 + seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours * 3600 + minutes * 60 + seconds)
    return 0.0


def _infer_horizontal_lane(shot_type: str, *, sample_index: int, right_bias: float) -> float:
    shot = shot_type.lower()
    if "cross-court" in shot:
        return 0.78 if sample_index % 2 == 0 else 0.22
    if "backhand" in shot:
        return 0.28
    if "forehand" in shot:
        return 0.72
    return 0.38 + min(max(right_bias, 0.0), 1.0) * 0.24


def _infer_vertical_lane(shot_type: str) -> float:
    shot = shot_type.lower()
    if "net" in shot:
        return 0.18
    if "drop" in shot or "smash" in shot:
        return 0.3
    if "drive" in shot:
        return 0.48
    if "clear" in shot or "lift" in shot:
        return 0.82
    return 0.52


def _sample_confidence(
    event: ShotSelectionEvent,
    *,
    tracking_summary: PlayerTrackSummary | None,
) -> float:
    base = 0.42 + (event.execution_score / 250.0) + (event.decision_score / 400.0)
    if tracking_summary is not None:
        base += 0.08
    return min(max(base, 0.05), 0.92)


def _build_shuttle_samples(
    shot_selection: ShotSelectionMetrics,
    *,
    tracking_summary: PlayerTrackSummary | None,
) -> list[ShuttleSample]:
    if tracking_summary is not None:
        right_bias = tracking_summary.directional_balance.get("right", 0.5)
    else:
        right_bias = 0.5

    samples: list[ShuttleSample] = []
    for sample_index, event in enumerate(shot_selection.events):
        samples.append(
            ShuttleSample(
                timestamp_seconds=_parse_timestamp(event.timestamp),
                x=_infer_horizontal_lane(
                    event.shot_type,
                    sample_index=sample_index,
                    right_bias=right_bias,
                ),
                y=_infer_vertical_lane(event.shot_type),
                confidence=_sample_confidence(event, tracking_summary=tracking_summary),
            )
        )
    return samples


def _build_gaussian_heatmap(samples: list[ShuttleSample]) -> list[HeatmapCell]:
    if not samples:
        return [HeatmapCell(zone=zone, weight=0.0) for zone in ZONE_CENTERS]

    raw_weights: list[tuple[str, float]] = []
    for zone, (zone_x, zone_y) in ZONE_CENTERS.items():
        score = 0.0
        for sample in samples:
            dx = sample.x - zone_x
            dy = sample.y - zone_y
            distance_sq = dx * dx + dy * dy
            score += sample.confidence * exp(-distance_sq / (2 * GAUSSIAN_SIGMA * GAUSSIAN_SIGMA))
        raw_weights.append((zone, score))

    total = sum(score for _, score in raw_weights) or 1.0
    return [HeatmapCell(zone=zone, weight=score / total) for zone, score in raw_weights]


def _pressure_label(y: float) -> str:
    if y < 0.34:
        return "Forecourt pressure"
    if y < 0.67:
        return "Midcourt exchange"
    return "Rear-court reset"


def _pressure_summary(label: str, start: str, end: str) -> str:
    if label == "Forecourt pressure":
        return f"Repeated front-court interceptions were inferred between {start} and {end}."
    if label == "Midcourt exchange":
        return (
            "The inferred shuttle path stayed flatter through the midcourt between "
            f"{start} and {end}."
        )
    return f"High lifts or clears appear to have reset the rally between {start} and {end}."


def _build_pressure_windows(
    shot_selection: ShotSelectionMetrics,
    samples: list[ShuttleSample],
) -> list[PressureWindow]:
    if not samples:
        return []

    windows: list[PressureWindow] = []
    start_index = 0
    current_label = _pressure_label(samples[0].y)

    for index in range(1, len(samples)):
        next_label = _pressure_label(samples[index].y)
        if next_label == current_label:
            continue

        start_timestamp = shot_selection.events[start_index].timestamp
        end_timestamp = shot_selection.events[index - 1].timestamp
        windows.append(
            PressureWindow(
                label=current_label,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                summary=_pressure_summary(current_label, start_timestamp, end_timestamp),
            )
        )
        start_index = index
        current_label = next_label

    start_timestamp = shot_selection.events[start_index].timestamp
    end_timestamp = shot_selection.events[len(samples) - 1].timestamp
    windows.append(
        PressureWindow(
            label=current_label,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            summary=_pressure_summary(current_label, start_timestamp, end_timestamp),
        )
    )
    return windows


def build_shuttle_metrics(
    shot_selection: ShotSelectionMetrics,
    *,
    tracking_summary: PlayerTrackSummary | None,
) -> ShuttleMetrics:
    samples = _build_shuttle_samples(shot_selection, tracking_summary=tracking_summary)
    heatmap = _build_gaussian_heatmap(samples)
    pressure_windows = _build_pressure_windows(shot_selection, samples)
    dominant_zone = max(
        heatmap,
        key=lambda cell: cell.weight,
        default=HeatmapCell(zone="mid-centre", weight=0),
    )
    dominant_label = dominant_zone.zone.replace("-", " ")
    inferred_windows = len(
        [window for window in pressure_windows if window.label == "Forecourt pressure"]
    )

    summary = (
        f"Gaussian-smoothed shuttle occupancy leaned most heavily toward the {dominant_label}, "
        f"with {inferred_windows} inferred forecourt pressure window(s)."
    )
    uncertainty_note = (
        "Shuttle positions are inferred from shot context and tracked-player movement, then "
        "smoothed into zone density rather than directly observed frame by frame."
    )
    return ShuttleMetrics(
        summary=summary,
        uncertainty_note=uncertainty_note,
        samples=samples,
        pressure_windows=pressure_windows,
        heatmap=heatmap,
    )


def build_analysis_evidence(
    analytics: AnalyticsView,
    *,
    tracking_summary: PlayerTrackSummary | None,
    pose_summary: PoseSummary | None,
) -> AnalysisEvidence:
    mechanics_note = (
        pose_summary.recovery_note
        if pose_summary is not None
        else analytics.mechanics.recovery_note
    )
    movement_summary = (
        f"Tracked distance was {analytics.movement.total_distance_meters:.1f}m with recovery score "
        f"{analytics.movement.recovery_score} and court coverage "
        f"{analytics.movement.court_coverage_percent}%."
    )
    return AnalysisEvidence(
        shuttle=analytics.shuttle,
        movement_summary=movement_summary,
        mechanics_summary=mechanics_note,
        shot_selection_summary=analytics.shot_selection.overview,
    )


def build_default_ai_rationale(analytics: AnalyticsView) -> AIRationale:
    top_window = (
        analytics.shuttle.pressure_windows[0].summary
        if analytics.shuttle.pressure_windows
        else analytics.shuttle.summary
    )
    return AIRationale(
        summary=(
            "The coaching summary was grounded in the expanded analytics and inferred "
            "shuttle evidence."
        ),
        evidence_highlights=[
            top_window,
            analytics.shot_selection.overview,
            analytics.mechanics.recovery_note,
        ],
    )
