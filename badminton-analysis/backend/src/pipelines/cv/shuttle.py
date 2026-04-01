from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Any

from schemas import DetectionBox, ShuttleSample, TrackSample


@dataclass(slots=True)
class ShuttleTrackingResult:
    samples: list[ShuttleSample] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def score_shuttle_candidate(
    *,
    area_px: float,
    speed_px: float,
    distance_to_track_px: float,
) -> float:
    size_score = max(0.0, 1.0 - min(area_px / 180.0, 1.0))
    speed_score = min(max(speed_px, 0.0) / 35.0, 1.0)
    separation_score = max(0.0, 1.0 - min(distance_to_track_px / 120.0, 1.0))
    return round(
        (size_score * 0.5) + (speed_score * 0.35) + (separation_score * 0.15),
        4,
    )


def detect_shuttle_samples(
    *,
    cv2: Any,
    frames_by_index: dict[int, Any],
    focused_samples: list[TrackSample],
) -> ShuttleTrackingResult:
    if len(frames_by_index) < 2 or len(focused_samples) < 2:
        return ShuttleTrackingResult(
            warnings=[
                "Shuttle observations were unavailable; analytics will use inferred fallback."
            ]
        )

    ordered_samples = sorted(focused_samples, key=lambda sample: sample.frame_index)
    previous_gray: Any | None = None
    observed_samples: list[ShuttleSample] = []

    for sample in ordered_samples:
        frame = frames_by_index.get(sample.frame_index)
        if frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        if previous_gray is None:
            previous_gray = gray
            continue

        frame_delta = cv2.absdiff(gray, previous_gray)
        _, threshold = cv2.threshold(frame_delta, 18, 255, cv2.THRESH_BINARY)
        threshold = cv2.dilate(threshold, None, iterations=2)
        contours_info = cv2.findContours(
            threshold,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

        height, width = frame.shape[:2]
        best_candidate: ShuttleSample | None = None
        best_score = 0.0

        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area <= 0:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if w <= 0 or h <= 0:
                continue

            center_x = x + (w / 2)
            center_y = y + (h / 2)
            score = score_shuttle_candidate(
                area_px=area,
                speed_px=hypot(float(w), float(h)),
                distance_to_track_px=_distance_to_player(
                    center_x,
                    center_y,
                    sample.bounding_box,
                    width=width,
                    height=height,
                ),
            )
            if score <= best_score or score < 0.45:
                continue

            best_score = score
            best_candidate = ShuttleSample(
                timestamp_seconds=sample.timestamp_seconds,
                x=max(0.0, min(1.0, center_x / width)),
                y=max(0.0, min(1.0, center_y / height)),
                confidence=min(best_score, 0.99),
                source="observed",
            )

        if best_candidate is not None:
            observed_samples.append(best_candidate)

        previous_gray = gray

    if observed_samples:
        return ShuttleTrackingResult(samples=observed_samples)

    return ShuttleTrackingResult(
        warnings=[
            "Shuttle observations were unavailable; analytics will use inferred fallback."
        ]
    )


def _distance_to_player(
    x: float,
    y: float,
    box: DetectionBox | None,
    *,
    width: int,
    height: int,
) -> float:
    if box is None:
        return 0.0
    player_x = (box.x + (box.width / 2)) * width
    player_y = (box.y + (box.height / 2)) * height
    return hypot(x - player_x, y - player_y)
