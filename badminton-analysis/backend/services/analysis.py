import math

import cv2
import numpy as np

from models.schemas import AnalysisStats, MovementPoint, BoundingBox

# Approximate court length in meters for distance normalization
COURT_LENGTH_M = 13.4
COURT_GRID_CELLS = 20


def compute_stats(
    frame_data: list[dict],
    frame_width: int,
    frame_height: int,
) -> AnalysisStats:
    if len(frame_data) < 2:
        return AnalysisStats(
            total_distance_meters=0,
            avg_speed_mps=0,
            court_coverage_pct=0,
            estimated_shot_count=0,
            movement_over_time=[],
        )

    # Pixel-to-meter scale: assume frame height ~ court length
    px_to_m = COURT_LENGTH_M / frame_height

    # Distance and movement over time
    total_distance_px = 0.0
    movement_over_time = []
    cumulative_distance = 0.0

    for i in range(1, len(frame_data)):
        dx = frame_data[i]["center_x"] - frame_data[i - 1]["center_x"]
        dy = frame_data[i]["center_y"] - frame_data[i - 1]["center_y"]
        dist = math.sqrt(dx * dx + dy * dy)
        total_distance_px += dist
        cumulative_distance += dist * px_to_m
        movement_over_time.append(MovementPoint(
            time_sec=round(frame_data[i]["time_sec"], 2),
            distance=round(cumulative_distance, 2),
        ))

    total_distance_m = total_distance_px * px_to_m
    total_time = frame_data[-1]["time_sec"] - frame_data[0]["time_sec"]
    avg_speed = total_distance_m / total_time if total_time > 0 else 0.0

    # Court coverage: divide frame into grid, count visited cells
    cell_w = frame_width / COURT_GRID_CELLS
    cell_h = frame_height / COURT_GRID_CELLS
    visited = set()
    for fd in frame_data:
        col = int(fd["center_x"] / cell_w) if cell_w > 0 else 0
        row = int(fd["center_y"] / cell_h) if cell_h > 0 else 0
        visited.add((row, col))
    total_cells = COURT_GRID_CELLS * COURT_GRID_CELLS
    coverage_pct = (len(visited) / total_cells) * 100

    # Shot detection: wrist acceleration spikes
    shot_count = _detect_shots(frame_data)

    return AnalysisStats(
        total_distance_meters=round(total_distance_m, 2),
        avg_speed_mps=round(avg_speed, 2),
        court_coverage_pct=round(coverage_pct, 1),
        estimated_shot_count=shot_count,
        movement_over_time=movement_over_time,
    )


def _detect_shots(frame_data: list[dict]) -> int:
    wrist_positions = []
    for fd in frame_data:
        lms = fd.get("landmarks")
        if lms is None:
            wrist_positions.append(None)
            continue
        wrist = None
        for lm in lms:
            if lm["name"] in ("RIGHT_WRIST", "LEFT_WRIST"):
                if wrist is None or lm["visibility"] > wrist["visibility"]:
                    wrist = lm
        wrist_positions.append(wrist)

    # Compute wrist speed between frames
    speeds = []
    for i in range(1, len(wrist_positions)):
        if wrist_positions[i] is None or wrist_positions[i - 1] is None:
            speeds.append(0.0)
            continue
        dx = wrist_positions[i]["x"] - wrist_positions[i - 1]["x"]
        dy = wrist_positions[i]["y"] - wrist_positions[i - 1]["y"]
        speeds.append(math.sqrt(dx * dx + dy * dy))

    if not speeds:
        return 0

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    threshold = max(avg_speed * 1.5, 10)  # 1.5x average or at least 10px

    shot_count = 0
    cooldown = 0
    for s in speeds:
        if cooldown > 0:
            cooldown -= 1
            continue
        if s > threshold:
            shot_count += 1
            cooldown = 5  # Skip 5 frames after a shot to avoid double-counting

    return shot_count


def render_annotated_video(
    video_path: str,
    output_path: str,
    tracked_boxes: list[BoundingBox | None],
    all_landmarks: list[list[dict] | None],
    positions: list[tuple[float, float]],
) -> None:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    trail = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx < len(tracked_boxes) and tracked_boxes[frame_idx] is not None:
            box = tracked_boxes[frame_idx]
            # Draw bounding box
            x, y, w, h = int(box.x), int(box.y), int(box.width), int(box.height)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if frame_idx < len(positions):
            trail.append(positions[frame_idx])

        # Draw movement trail
        for i in range(1, len(trail)):
            pt1 = (int(trail[i - 1][0]), int(trail[i - 1][1]))
            pt2 = (int(trail[i][0]), int(trail[i][1]))
            cv2.line(frame, pt1, pt2, (255, 165, 0), 2)

        # Draw pose skeleton
        if frame_idx < len(all_landmarks) and all_landmarks[frame_idx] is not None:
            lms = all_landmarks[frame_idx]
            _draw_skeleton(frame, lms)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()


def _draw_skeleton(frame: np.ndarray, landmarks: list[dict]) -> None:
    """Draw pose skeleton connections on frame."""
    # Define pose connections (MediaPipe pose landmarks)
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 7),  # Head to shoulders
        (0, 4), (4, 5), (5, 6), (6, 8),  # Head to other shoulder
        (9, 10), (11, 12), (11, 13), (13, 15),  # Arms
        (12, 14), (14, 16),  # Other arm
        (11, 23), (12, 24), (23, 24),  # Torso
        (23, 25), (25, 27), (27, 29), (27, 31),  # Left leg
        (24, 26), (26, 28), (28, 30), (30, 32),  # Right leg
    ]

    # Create landmark map for quick lookup
    lm_map = {lm["name"]: (int(lm["x"]), int(lm["y"])) for lm in landmarks}

    # Draw connections
    for start_idx, end_idx in connections:
        start_name = f"LANDMARK_{start_idx}"
        end_name = f"LANDMARK_{end_idx}"
        if start_name in lm_map and end_name in lm_map:
            cv2.line(frame, lm_map[start_name], lm_map[end_name], (0, 255, 255), 2)

    # Draw landmark points
    for lm in landmarks:
        if lm["visibility"] > 0.5:
            cv2.circle(frame, (int(lm["x"]), int(lm["y"])), 3, (0, 0, 255), -1)
