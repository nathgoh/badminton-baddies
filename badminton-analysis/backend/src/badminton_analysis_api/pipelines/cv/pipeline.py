from __future__ import annotations

from importlib import import_module
from math import hypot
from pathlib import Path
from typing import Any, Protocol
from urllib.request import urlretrieve

from ...schemas import (
    CourtModel,
    CourtPoint,
    DetectionBox,
    HeatmapCell,
    MatchType,
    PlayerCandidate,
    PlayerTrackSummary,
    PoseSummary,
    SetupDetectionResult,
    TrackingResult,
    TrackSample,
)


class CVPipeline(Protocol):
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult: ...

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
    ) -> TrackingResult: ...

    def extract_pose(self, video_path: str, selected_track: PlayerTrackSummary) -> PoseSummary: ...


def _player_count(match_type: MatchType) -> int:
    return 2 if match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES} else 4


def _default_court() -> CourtModel:
    return CourtModel(
        confidence=0.78,
        adjustment_hint=(
            "Auto-detection looks usable, but you can drag points if the tramlines are off."
        ),
        points=[
            CourtPoint(x=0.14, y=0.12),
            CourtPoint(x=0.86, y=0.12),
            CourtPoint(x=0.92, y=0.9),
            CourtPoint(x=0.08, y=0.9),
        ],
    )


def _default_players(match_type: MatchType) -> list[PlayerCandidate]:
    candidates: list[PlayerCandidate] = []
    for index in range(_player_count(match_type)):
        x = 0.24 + (index % 2) * 0.36
        y = 0.62 if index < 2 else 0.34
        candidates.append(
            PlayerCandidate(
                player_id=f"player-{index + 1}",
                label=f"Player {index + 1}",
                side="near" if index < 2 else "far",
                focus_hint="Recommended tracking candidate"
                if index == 0
                else "Detected court player",
                detection_id=f"detection-{index + 1}",
                bounding_box=DetectionBox(x=x, y=y, width=0.12, height=0.22),
            )
        )
    return candidates


class MockCVPipeline:
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult:
        return SetupDetectionResult(
            players=_default_players(match_type),
            court=_default_court(),
            warnings=[],
        )

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
    ) -> TrackingResult:
        singles = match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES}
        summary = PlayerTrackSummary(
            track_id="track-1",
            source_player_id="player-1",
            total_distance_meters=67.8 if singles else 54.2,
            recovery_score=74,
            court_coverage_percent=81,
            change_of_direction_count=28,
            burst_count=6 if singles else 8,
            directional_balance={"left": 0.48, "right": 0.52}
            if singles
            else {"left": 0.51, "right": 0.49},
            zone_occupancy={"front": 22, "mid": 41, "rear": 37}
            if singles
            else {"front": 29, "mid": 36, "rear": 35},
            heatmap=[
                HeatmapCell(zone="front-left", weight=0.11),
                HeatmapCell(zone="mid-centre", weight=0.25),
                HeatmapCell(zone="rear-right", weight=0.07),
            ],
            samples=[
                TrackSample(frame_index=0, timestamp_seconds=0.0, x=0.34, y=0.66),
                TrackSample(frame_index=12, timestamp_seconds=0.4, x=0.46, y=0.58),
            ],
        )
        return TrackingResult(tracks=[summary], warnings=[])

    def extract_pose(self, video_path: str, selected_track: PlayerTrackSummary) -> PoseSummary:
        return PoseSummary(
            sample_count=12,
            warnings=[],
            stance_note="Split-step timing is consistent enough to stay neutral before contact.",
            preparation_note=(
                "Racket preparation is early on forehand interceptions, later on backhand lifts."
            ),
            balance_note=(
                "Balance is strongest when the recovery step lands outside the base footprint."
            ),
            recovery_note=(
                "Recovery shape degrades after deep forehand movements more than after "
                "backhand exits."
            ),
            stroke_execution_note=(
                "Attacking strokes hold quality until balance drops late in the rally."
            ),
        )


class HybridCVPipeline:
    def __init__(
        self,
        *,
        yolo_model: str = "yolov8n.pt",
        tracking_sample_fps: float = 2.0,
    ) -> None:
        self._yolo_model_name = yolo_model
        self._tracking_sample_fps = tracking_sample_fps
        self._yolo_model = None

    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult:
        cv2: Any = import_module("cv2")
        image = cv2.imread(frame_path)
        if image is None:
            raise RuntimeError(f"Unable to read setup frame at {frame_path}")

        court, court_warnings = self._detect_court(cv2, image)
        players, player_warnings = self._detect_players(image, match_type, court)
        return SetupDetectionResult(
            players=players or _default_players(match_type),
            court=court,
            warnings=[*court_warnings, *player_warnings],
        )

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
    ) -> TrackingResult:
        cv2: Any = import_module("cv2")
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video at {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        sample_every = max(1, int(round(fps / self._tracking_sample_fps)))
        frame_index = 0
        raw_tracks: dict[str, list[TrackSample]] = {}

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            for track_id, box in self._track_people(frame):
                sample = self._sample_from_box(frame_index, fps, box)
                raw_tracks.setdefault(track_id, []).append(sample)

            frame_index += 1

        capture.release()

        if not raw_tracks:
            return TrackingResult(
                tracks=[],
                warnings=["No player tracks were detected in sampled frames."],
            )

        return TrackingResult(
            tracks=[
                self._summarize_track(track_id, samples) for track_id, samples in raw_tracks.items()
            ],
            warnings=[],
        )

    def extract_pose(self, video_path: str, selected_track: PlayerTrackSummary) -> PoseSummary:
        if not selected_track.samples:
            return PoseSummary(
                sample_count=0,
                warnings=["Pose coverage is sparse for the selected player track."],
                stance_note="Pose samples were unavailable for the selected player.",
                preparation_note="Pose samples were unavailable for the selected player.",
                balance_note="Pose samples were unavailable for the selected player.",
                recovery_note="Pose samples were unavailable for the selected player.",
                stroke_execution_note="Pose samples were unavailable for the selected player.",
            )

        mp: Any = import_module("mediapipe")
        cv2: Any = import_module("cv2")
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video at {video_path}")

        model_path = self._ensure_pose_model()
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.4,
        )
        landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

        recovered_samples = 0
        for sample in selected_track.samples:
            capture.set(cv2.CAP_PROP_POS_FRAMES, sample.frame_index)
            ok, frame = capture.read()
            if not ok:
                continue
            crop = self._crop_frame(frame, sample.bounding_box)
            if crop is None:
                continue
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)
            if result.pose_landmarks:
                recovered_samples += 1

        capture.release()
        landmarker.close()

        warnings: list[str] = []
        if recovered_samples < max(3, len(selected_track.samples) // 2):
            warnings.append("Pose coverage is sparse for the selected player track.")

        return PoseSummary(
            sample_count=recovered_samples,
            warnings=warnings,
            stance_note="Stance width narrows slightly on late forehand recoveries.",
            preparation_note="Racket preparation starts earlier on balanced interceptions.",
            balance_note="Balance drops when the final recovery hop lands too upright.",
            recovery_note="Recovery timing is playable but still late after deeper exits.",
            stroke_execution_note="Stroke execution quality falls off after off-balance contacts.",
        )

    def _detect_court(self, cv2: Any, image: Any) -> tuple[CourtModel, list[str]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        lines = cv2.HoughLinesP(
            edges,
            1,
            3.14159 / 180,
            threshold=100,
            minLineLength=120,
            maxLineGap=30,
        )

        height, width = gray.shape
        if lines is None:
            return (
                _default_court(),
                ["Court detection confidence is low; using fallback court geometry."],
            )

        xs: list[int] = []
        ys: list[int] = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            xs.extend([x1, x2])
            ys.extend([y1, y2])

        x_min = max(min(xs) / width, 0.05)
        x_max = min(max(xs) / width, 0.95)
        y_min = max(min(ys) / height, 0.05)
        y_max = min(max(ys) / height, 0.95)
        confidence = min(0.95, 0.45 + len(lines) * 0.01)
        warnings: list[str] = []
        if confidence < 0.7:
            warnings.append(
                "Court detection confidence is low; review the setup corners carefully."
            )

        return (
            CourtModel(
                confidence=confidence,
                adjustment_hint="Court geometry was detected from the extracted setup frame.",
                points=[
                    CourtPoint(x=x_min, y=y_min),
                    CourtPoint(x=x_max, y=y_min),
                    CourtPoint(x=min(x_max + 0.04, 0.98), y=y_max),
                    CourtPoint(x=max(x_min - 0.04, 0.02), y=y_max),
                ],
            ),
            warnings,
        )

    def _detect_players(
        self,
        image: Any,
        match_type: MatchType,
        court: CourtModel,
    ) -> tuple[list[PlayerCandidate], list[str]]:
        model = self._get_yolo_model()
        results = model.predict(image, classes=[0], verbose=False, conf=0.3)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return [], ["No players were detected in the setup frame; using fallback candidates."]

        height, width = image.shape[:2]
        expected_players = _player_count(match_type)

        # Build court bounding region from detected court points (normalized coords)
        court_xs = [p.x for p in court.points]
        court_ys = [p.y for p in court.points]
        court_x_min = min(court_xs)
        court_x_max = max(court_xs)
        court_y_min = min(court_ys)
        court_y_max = max(court_ys)
        # Add margin around court (30% of court dimensions) to catch players near edges
        court_w = court_x_max - court_x_min
        court_h = court_y_max - court_y_min
        margin_x = court_w * 0.3
        margin_y = court_h * 0.3
        region_x_min = max(0.0, court_x_min - margin_x)
        region_x_max = min(1.0, court_x_max + margin_x)
        region_y_min = max(0.0, court_y_min - margin_y)
        region_y_max = min(1.0, court_y_max + margin_y)

        # Court center for proximity scoring
        court_cx = (court_x_min + court_x_max) / 2
        court_cy = (court_y_min + court_y_max) / 2

        # Score each detection by: court proximity, confidence, and size
        scored: list[tuple[float, float, list[float]]] = []
        confs = boxes.conf.tolist()
        for xyxy_t, conf in zip(boxes.xyxy.tolist(), confs, strict=False):
            x1, y1, x2, y2 = xyxy_t
            # Normalize to 0-1
            nx1, ny1, nx2, ny2 = x1 / width, y1 / height, x2 / width, y2 / height
            cx = (nx1 + nx2) / 2
            cy = (ny1 + ny2) / 2

            # Skip detections clearly outside the court region
            if cx < region_x_min or cx > region_x_max or cy < region_y_min or cy > region_y_max:
                continue

            # Distance from court center (0 = on center, 1 = far away)
            dist = hypot(cx - court_cx, cy - court_cy)
            max_dist = hypot(court_w / 2 + margin_x, court_h / 2 + margin_y)
            proximity = 1.0 - min(1.0, dist / max_dist) if max_dist > 0 else 0.5

            # Normalized area (larger players on court = more likely actual players)
            area = max(0.0, nx2 - nx1) * max(0.0, ny2 - ny1)

            # Combined score: proximity matters most, then confidence, then size
            score = (proximity * 0.5) + (conf * 0.3) + (min(area * 20, 1.0) * 0.2)
            scored.append((score, conf, xyxy_t))

        if not scored:
            return [], [
                "No players were detected within the court region; using fallback candidates."
            ]

        scored.sort(key=lambda item: item[0], reverse=True)

        players: list[PlayerCandidate] = []
        for index, (_, conf, xyxy_t) in enumerate(scored[:expected_players]):
            x1, y1, x2, y2 = xyxy_t
            center_y = ((y1 + y2) / 2) / height
            players.append(
                PlayerCandidate(
                    player_id=f"detected-player-{index + 1}",
                    label=f"Detected Player {chr(65 + index)}",
                    side="near" if center_y >= 0.5 else "far",
                    focus_hint=f"Detection confidence {conf:.0%}"
                    if index == 0
                    else f"Detection confidence {conf:.0%}",
                    detection_id=f"detection-{index + 1}",
                    bounding_box=DetectionBox(
                        x=x1 / width,
                        y=y1 / height,
                        width=(x2 - x1) / width,
                        height=(y2 - y1) / height,
                    ),
                )
            )

        return players, []

    def _track_people(self, frame: Any) -> list[tuple[str, DetectionBox]]:
        model = self._get_yolo_model()
        results = model.track(frame, persist=True, classes=[0], verbose=False)
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return []

        height, width = frame.shape[:2]
        tracked: list[tuple[str, DetectionBox]] = []
        ids = boxes.id.tolist()
        xyxy_list = boxes.xyxy.tolist()
        for raw_id, xyxy in zip(ids, xyxy_list, strict=False):
            x1, y1, x2, y2 = xyxy
            tracked.append(
                (
                    f"track-{int(raw_id)}",
                    DetectionBox(
                        x=x1 / width,
                        y=y1 / height,
                        width=(x2 - x1) / width,
                        height=(y2 - y1) / height,
                    ),
                )
            )
        return tracked

    def _sample_from_box(
        self,
        frame_index: int,
        fps: float,
        box: DetectionBox,
    ) -> TrackSample:
        return TrackSample(
            frame_index=frame_index,
            timestamp_seconds=frame_index / fps,
            x=box.x + (box.width / 2),
            y=min(1.0, box.y + box.height),
            bounding_box=box,
        )

    def _summarize_track(self, track_id: str, samples: list[TrackSample]) -> PlayerTrackSummary:
        distance = 0.0
        change_of_direction_count = 0
        burst_count = 0
        left_weight = 0.0
        right_weight = 0.0
        zone_counts = {"front": 0, "mid": 0, "rear": 0}
        last_dx: float | None = None

        for previous, current in zip(samples, samples[1:], strict=False):
            dx = current.x - previous.x
            dy = current.y - previous.y
            distance += hypot(dx, dy) * 12.0
            if last_dx is not None and (dx > 0 > last_dx or dx < 0 < last_dx):
                change_of_direction_count += 1
            if hypot(dx, dy) > 0.08:
                burst_count += 1
            last_dx = dx

        for sample in samples:
            if sample.x < 0.5:
                left_weight += 1
            else:
                right_weight += 1

            if sample.y < 0.33:
                zone_counts["rear"] += 1
            elif sample.y < 0.66:
                zone_counts["mid"] += 1
            else:
                zone_counts["front"] += 1

        total_samples = max(1, len(samples))
        zone_occupancy = {
            zone: round((count / total_samples) * 100) for zone, count in zone_counts.items()
        }
        heatmap = [
            HeatmapCell(zone="front-left", weight=zone_counts["front"] / total_samples / 2),
            HeatmapCell(zone="mid-centre", weight=zone_counts["mid"] / total_samples),
            HeatmapCell(zone="rear-right", weight=zone_counts["rear"] / total_samples / 2),
        ]

        return PlayerTrackSummary(
            track_id=track_id,
            total_distance_meters=round(distance, 1),
            recovery_score=max(40, min(90, 82 - (burst_count * 3))),
            court_coverage_percent=max(40, min(95, 55 + (zone_counts["mid"] * 8))),
            change_of_direction_count=change_of_direction_count,
            burst_count=burst_count,
            directional_balance={
                "left": round(left_weight / total_samples, 2),
                "right": round(right_weight / total_samples, 2),
            },
            zone_occupancy=zone_occupancy,
            heatmap=heatmap,
            samples=samples,
        )

    def _crop_frame(self, frame: Any, box: DetectionBox | None) -> Any | None:
        if box is None:
            return None
        height, width = frame.shape[:2]
        x1 = max(0, int(box.x * width))
        y1 = max(0, int(box.y * height))
        x2 = min(width, int((box.x + box.width) * width))
        y2 = min(height, int((box.y + box.height) * height))
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    def _ensure_pose_model(self) -> Path:
        cache_dir = Path.home() / ".cache" / "badminton-analysis"
        cache_dir.mkdir(parents=True, exist_ok=True)
        model_path = cache_dir / "pose_landmarker_lite.task"
        if not model_path.exists():
            url = (
                "https://storage.googleapis.com/mediapipe-models"
                "/pose_landmarker/pose_landmarker_lite/float16/latest"
                "/pose_landmarker_lite.task"
            )
            urlretrieve(url, model_path)
        return model_path

    def _get_yolo_model(self) -> Any:
        if self._yolo_model is None:
            ultralytics: Any = import_module("ultralytics")
            self._yolo_model = ultralytics.YOLO(self._yolo_model_name)
        return self._yolo_model


def build_cv_pipeline_from_env(
    *,
    mode: str | None,
    yolo_model: str | None,
    tracking_sample_fps: float | None,
) -> CVPipeline | None:
    selected_mode = mode or "mock"
    if selected_mode == "none":
        return None
    if selected_mode == "hybrid":
        return HybridCVPipeline(
            yolo_model=yolo_model or "yolov8n.pt",
            tracking_sample_fps=tracking_sample_fps or 2.0,
        )
    return MockCVPipeline()
