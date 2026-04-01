from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import cv2
import numpy as np

from schemas import (
    CourtModel,
    DetectionBox,
    MatchType,
    PlayerCandidate,
    PlayerTrackSummary,
    TrackSample,
)


@dataclass(slots=True)
class ProjectedTrackSummary:
    total_distance_meters: float


@dataclass(slots=True)
class CourtHomography:
    matrix: np.ndarray
    source_polygon: np.ndarray
    width_meters: float
    height_meters: float


def _canonicalize_court_points(points: list[tuple[float, float]]) -> np.ndarray:
    if len(points) != 4:
        raise ValueError("Court calibration requires exactly four court points")

    source_points = np.array(points, dtype=np.float32)
    if np.unique(source_points, axis=0).shape[0] != 4:
        raise ValueError("Court calibration points must be unique")

    centroid = source_points.mean(axis=0)
    angles = np.arctan2(source_points[:, 1] - centroid[1], source_points[:, 0] - centroid[0])
    ordered = source_points[np.argsort(angles)]
    top_left_index = int(np.argmin(ordered[:, 0] + ordered[:, 1]))
    ordered = np.roll(ordered, -top_left_index, axis=0)

    contour = ordered.reshape(-1, 1, 2)
    if not cv2.isContourConvex(contour):
        raise ValueError("Court calibration points must form a convex court polygon")
    if cv2.contourArea(contour) <= 1e-6:
        raise ValueError("Court calibration polygon is degenerate")

    return ordered


def build_court_homography(court: CourtModel, match_type: MatchType) -> CourtHomography:
    width_m = 5.18 if match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES} else 6.10
    height_m = 13.40
    ordered_points = _canonicalize_court_points([(point.x, point.y) for point in court.points])

    target_points = np.array(
        [[0.0, 0.0], [width_m, 0.0], [width_m, height_m], [0.0, height_m]], dtype=np.float32
    )
    return CourtHomography(
        matrix=cv2.getPerspectiveTransform(ordered_points, target_points),
        source_polygon=ordered_points.reshape(-1, 1, 2),
        width_meters=width_m,
        height_meters=height_m,
    )


def summarize_projected_track(
    samples: list[TrackSample], homography: CourtHomography | np.ndarray
) -> ProjectedTrackSummary:
    if len(samples) < 2:
        return ProjectedTrackSummary(total_distance_meters=0.0)

    if isinstance(homography, CourtHomography):
        matrix = homography.matrix
        source_polygon = homography.source_polygon
    else:
        matrix = homography
        source_polygon = None

    distance = 0.0
    projected_point: np.ndarray | None = None
    for sample in samples:
        if source_polygon is not None:
            location = cv2.pointPolygonTest(
                source_polygon, (float(sample.x), float(sample.y)), False
            )
            if location < 0:
                continue

        point = np.array([[[sample.x, sample.y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(point, matrix)[0, 0]
        if projected_point is not None:
            distance += hypot(
                float(projected[0] - projected_point[0]),
                float(projected[1] - projected_point[1]),
            )
        projected_point = projected

    return ProjectedTrackSummary(total_distance_meters=distance)


def select_focused_track_id(
    selected_player: PlayerCandidate,
    tracks: list[PlayerTrackSummary],
    first_boxes: dict[str, DetectionBox],
) -> str | None:
    if selected_player.bounding_box is None:
        return None

    def iou(left: DetectionBox, right: DetectionBox) -> float:
        x1 = max(left.x, right.x)
        y1 = max(left.y, right.y)
        x2 = min(left.x + left.width, right.x + right.width)
        y2 = min(left.y + left.height, right.y + right.height)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        intersection = (x2 - x1) * (y2 - y1)
        left_area = left.width * left.height
        right_area = right.width * right.height
        return intersection / max(left_area + right_area - intersection, 1e-6)

    selected = selected_player.bounding_box
    selected_center_x = selected.x + selected.width / 2
    selected_center_y = selected.y + selected.height / 2

    best_track_id: str | None = None
    best_iou = 0.0
    best_center_distance = float("inf")
    for track in tracks:
        candidate = first_boxes.get(track.track_id)
        if candidate is None:
            continue

        center_dx = (candidate.x + candidate.width / 2) - selected_center_x
        center_dy = (candidate.y + candidate.height / 2) - selected_center_y
        overlap = iou(selected, candidate)
        center_distance = hypot(center_dx, center_dy)
        if overlap > best_iou or (overlap == best_iou and center_distance < best_center_distance):
            best_iou = overlap
            best_center_distance = center_distance
            best_track_id = track.track_id

    return best_track_id if best_iou > 0.0 else None
