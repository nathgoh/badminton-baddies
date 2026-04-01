from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from math import acos, atan2, degrees, hypot
from pathlib import Path
from typing import Any, Protocol
from urllib.request import urlretrieve

from schemas import (
    CourtModel,
    CourtPoint,
    DetectionBox,
    HeatmapCell,
    MatchType,
    PlayerCandidate,
    PlayerTrackSummary,
    PoseFrame,
    PoseLandmarkPoint,
    PoseMechanicsMetrics,
    PoseSummary,
    SetupDetectionResult,
    TrackingResult,
    TrackSample,
)

from .geometry import build_court_homography, select_focused_track_id, summarize_projected_track
from .overlay import draw_player_pose_overlay
from .shuttle import detect_shuttle_samples

# Callback receives: (frame_index, total_frames, jpeg_bytes | None)
FrameCallback = Callable[[int, int, bytes | None], None]

_NOSE_INDEX = 0
_LEFT_SHOULDER_INDEX = 11
_RIGHT_SHOULDER_INDEX = 12
_LEFT_ELBOW_INDEX = 13
_RIGHT_ELBOW_INDEX = 14
_LEFT_WRIST_INDEX = 15
_RIGHT_WRIST_INDEX = 16
_LEFT_HIP_INDEX = 23
_RIGHT_HIP_INDEX = 24
_LEFT_KNEE_INDEX = 25
_RIGHT_KNEE_INDEX = 26
_LEFT_ANKLE_INDEX = 27
_RIGHT_ANKLE_INDEX = 28


class CVPipeline(Protocol):
    def detect_setup(self, frame_path: str, match_type: MatchType) -> SetupDetectionResult: ...

    def track_players(
        self,
        video_path: str,
        court: CourtModel,
        match_type: MatchType,
        *,
        selected_player: PlayerCandidate | None = None,
        on_frame: FrameCallback | None = None,
    ) -> TrackingResult: ...

    def extract_pose(
        self,
        video_path: str,
        selected_track: PlayerTrackSummary,
        *,
        on_frame: FrameCallback | None = None,
    ) -> PoseSummary: ...


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
        *,
        selected_player: PlayerCandidate | None = None,
        on_frame: FrameCallback | None = None,
    ) -> TrackingResult:
        singles = match_type in {MatchType.MENS_SINGLES, MatchType.WOMENS_SINGLES}
        source_player_id = selected_player.player_id if selected_player is not None else "player-1"
        summary = PlayerTrackSummary(
            track_id="track-1",
            source_player_id=source_player_id,
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
        return TrackingResult(
            tracks=[summary],
            focused_track_id=summary.track_id if selected_player is not None else None,
            warnings=[],
        )

    def extract_pose(
        self,
        video_path: str,
        selected_track: PlayerTrackSummary,
        *,
        on_frame: FrameCallback | None = None,
    ) -> PoseSummary:
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
        yolo_model: str = "yolo26n.pt",
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
        *,
        selected_player: PlayerCandidate | None = None,
        on_frame: FrameCallback | None = None,
    ) -> TrackingResult:
        cv2: Any = import_module("cv2")
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video at {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        total_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample_every = max(1, int(round(fps / self._tracking_sample_fps)))
        frame_index = 0
        raw_tracks: dict[str, list[TrackSample]] = {}
        first_boxes: dict[str, DetectionBox] = {}
        sampled_frames: dict[int, Any] = {}

        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            sampled_frames[frame_index] = frame.copy()
            detections = self._track_people(frame)
            for track_id, box in detections:
                first_boxes.setdefault(track_id, box)
                sample = self._sample_from_box(frame_index, fps, box)
                raw_tracks.setdefault(track_id, []).append(sample)

            if on_frame is not None:
                jpeg_bytes = self._annotate_frame(cv2, frame, detections)
                on_frame(frame_index, total_frame_count, jpeg_bytes)

            frame_index += 1

        capture.release()

        if not raw_tracks:
            return TrackingResult(
                tracks=[],
                warnings=["No player tracks were detected in sampled frames."],
            )

        tracks = [
            self._summarize_track(track_id, samples, court, match_type)
            for track_id, samples in raw_tracks.items()
        ]
        focused_track_id = None
        observed_shuttle_samples = []
        shuttle_warnings: list[str] = []
        if selected_player is not None:
            focused_track_id = select_focused_track_id(selected_player, tracks, first_boxes)
            if focused_track_id is not None:
                shuttle_result = detect_shuttle_samples(
                    cv2=cv2,
                    frames_by_index=sampled_frames,
                    focused_samples=raw_tracks.get(focused_track_id, []),
                )
                observed_shuttle_samples = shuttle_result.samples
                shuttle_warnings = shuttle_result.warnings

        return TrackingResult(
            tracks=tracks,
            focused_track_id=focused_track_id,
            observed_shuttle_samples=observed_shuttle_samples,
            warnings=shuttle_warnings,
        )

    def extract_pose(
        self,
        video_path: str,
        selected_track: PlayerTrackSummary,
        *,
        on_frame: FrameCallback | None = None,
    ) -> PoseSummary:
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

        total_samples = len(selected_track.samples)
        recovered_samples = 0
        pose_frames: list[PoseFrame] = []
        for sample_index, sample in enumerate(selected_track.samples):
            capture.set(cv2.CAP_PROP_POS_FRAMES, sample.frame_index)
            ok, frame = capture.read()
            if not ok:
                continue
            crop = self._crop_frame(frame, sample.bounding_box)
            detect_frame = crop if crop is not None else frame
            rgb = cv2.cvtColor(detect_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)
            if result.pose_landmarks:
                pose_frames.append(self._build_pose_frame(sample, result.pose_landmarks[0]))
                recovered_samples += 1

            if on_frame is not None:
                jpeg_bytes = self._annotate_pose(
                    cv2, frame, result.pose_landmarks, sample.bounding_box
                )
                on_frame(sample_index, total_samples, jpeg_bytes)

        capture.release()
        landmarker.close()

        warnings: list[str] = []
        if recovered_samples < max(3, len(selected_track.samples) // 2):
            warnings.append("Pose coverage is sparse for the selected player track.")

        mechanics = self._summarize_pose_mechanics(pose_frames)
        return PoseSummary(
            sample_count=recovered_samples,
            warnings=warnings,
            stance_note=self._stance_note(mechanics, recovered_samples),
            preparation_note=self._preparation_note(mechanics, recovered_samples),
            balance_note=self._balance_note(mechanics, recovered_samples),
            recovery_note=self._recovery_note(mechanics, recovered_samples),
            stroke_execution_note=self._stroke_execution_note(mechanics, recovered_samples),
            pose_frames=pose_frames,
            mechanics=mechanics,
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

    def _annotate_frame(
        self, cv2: Any, frame: Any, detections: list[tuple[str, DetectionBox]]
    ) -> bytes:
        """Draw bounding boxes on frame and return JPEG bytes."""
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        for track_id, box in detections:
            x1 = int(box.x * width)
            y1 = int(box.y * height)
            x2 = int((box.x + box.width) * width)
            y2 = int((box.y + box.height) * height)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated, track_id, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
            )
        _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return jpeg.tobytes()

    def _annotate_pose(
        self, cv2: Any, frame: Any, landmarks: Any, box: DetectionBox | None
    ) -> bytes:
        """Draw pose landmarks on frame and return JPEG bytes."""
        annotated = draw_player_pose_overlay(
            cv2,
            frame.copy(),
            box=box,
            poses=list(landmarks) if landmarks else None,
        )
        _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return jpeg.tobytes()

    def _build_pose_frame(self, sample: TrackSample, landmarks: Any) -> PoseFrame:
        return PoseFrame(
            frame_index=sample.frame_index,
            timestamp_seconds=sample.timestamp_seconds,
            landmarks=[self._pose_landmark_point(landmark) for landmark in landmarks],
        )

    def _pose_landmark_point(self, landmark: Any) -> PoseLandmarkPoint:
        return PoseLandmarkPoint(
            x=float(getattr(landmark, "x", 0.0)),
            y=float(getattr(landmark, "y", 0.0)),
            z=float(getattr(landmark, "z", 0.0)),
            visibility=self._optional_float(getattr(landmark, "visibility", None)),
        )

    def _summarize_pose_mechanics(self, pose_frames: list[PoseFrame]) -> PoseMechanicsMetrics:
        stance_width_ratios: list[float] = []
        knee_flexion_degrees: list[float] = []
        trunk_lean_degrees: list[float] = []
        balance_offsets: list[float] = []
        prepared_frames = 0

        for pose_frame in pose_frames:
            shoulder_width = self._distance_between(
                pose_frame, _LEFT_SHOULDER_INDEX, _RIGHT_SHOULDER_INDEX
            )
            ankle_width = self._distance_between(pose_frame, _LEFT_ANKLE_INDEX, _RIGHT_ANKLE_INDEX)
            if shoulder_width is not None and ankle_width is not None and shoulder_width > 0:
                stance_width_ratios.append(ankle_width / shoulder_width)

            left_knee_angle = self._joint_angle(
                pose_frame, _LEFT_HIP_INDEX, _LEFT_KNEE_INDEX, _LEFT_ANKLE_INDEX
            )
            right_knee_angle = self._joint_angle(
                pose_frame, _RIGHT_HIP_INDEX, _RIGHT_KNEE_INDEX, _RIGHT_ANKLE_INDEX
            )
            frame_knee_angles = [
                angle for angle in (left_knee_angle, right_knee_angle) if angle is not None
            ]
            if frame_knee_angles:
                knee_flexion_degrees.append(sum(frame_knee_angles) / len(frame_knee_angles))

            trunk_lean = self._trunk_lean_degrees(pose_frame)
            if trunk_lean is not None:
                trunk_lean_degrees.append(trunk_lean)

            balance_offset = self._balance_offset_ratio(pose_frame)
            if balance_offset is not None:
                balance_offsets.append(balance_offset)

            if self._is_prepared_frame(pose_frame):
                prepared_frames += 1

        total_frames = len(pose_frames)
        return PoseMechanicsMetrics(
            stance_width_ratio=self._rounded_average(stance_width_ratios),
            knee_flexion_degrees=self._rounded_average(knee_flexion_degrees),
            trunk_lean_degrees=self._rounded_average(trunk_lean_degrees),
            balance_offset_ratio=self._rounded_average(balance_offsets),
            preparation_rate=round(prepared_frames / total_frames, 2) if total_frames else None,
        )

    def _distance_between(
        self, pose_frame: PoseFrame, first_index: int, second_index: int
    ) -> float | None:
        first = self._landmark_xy(pose_frame, first_index)
        second = self._landmark_xy(pose_frame, second_index)
        if first is None or second is None:
            return None
        return hypot(second[0] - first[0], second[1] - first[1])

    def _joint_angle(
        self, pose_frame: PoseFrame, start_index: int, joint_index: int, end_index: int
    ) -> float | None:
        start = self._landmark_xy(pose_frame, start_index)
        joint = self._landmark_xy(pose_frame, joint_index)
        end = self._landmark_xy(pose_frame, end_index)
        if start is None or joint is None or end is None:
            return None

        vector_a = (start[0] - joint[0], start[1] - joint[1])
        vector_b = (end[0] - joint[0], end[1] - joint[1])
        magnitude_a = hypot(vector_a[0], vector_a[1])
        magnitude_b = hypot(vector_b[0], vector_b[1])
        if magnitude_a == 0 or magnitude_b == 0:
            return None

        dot_product = (vector_a[0] * vector_b[0]) + (vector_a[1] * vector_b[1])
        cosine = max(-1.0, min(1.0, dot_product / (magnitude_a * magnitude_b)))
        return degrees(acos(cosine))

    def _trunk_lean_degrees(self, pose_frame: PoseFrame) -> float | None:
        shoulder_midpoint = self._midpoint(pose_frame, _LEFT_SHOULDER_INDEX, _RIGHT_SHOULDER_INDEX)
        hip_midpoint = self._midpoint(pose_frame, _LEFT_HIP_INDEX, _RIGHT_HIP_INDEX)
        if shoulder_midpoint is None or hip_midpoint is None:
            return None

        dx = shoulder_midpoint[0] - hip_midpoint[0]
        dy = shoulder_midpoint[1] - hip_midpoint[1]
        return abs(degrees(atan2(dx, -dy)))

    def _balance_offset_ratio(self, pose_frame: PoseFrame) -> float | None:
        nose = self._landmark_xy(pose_frame, _NOSE_INDEX)
        ankle_midpoint = self._midpoint(pose_frame, _LEFT_ANKLE_INDEX, _RIGHT_ANKLE_INDEX)
        shoulder_width = self._distance_between(
            pose_frame, _LEFT_SHOULDER_INDEX, _RIGHT_SHOULDER_INDEX
        )
        if nose is None or ankle_midpoint is None or shoulder_width is None or shoulder_width == 0:
            return None

        return abs(nose[0] - ankle_midpoint[0]) / shoulder_width

    def _is_prepared_frame(self, pose_frame: PoseFrame) -> bool:
        left_wrist = self._landmark_xy(pose_frame, _LEFT_WRIST_INDEX)
        right_wrist = self._landmark_xy(pose_frame, _RIGHT_WRIST_INDEX)
        left_shoulder = self._landmark_xy(pose_frame, _LEFT_SHOULDER_INDEX)
        right_shoulder = self._landmark_xy(pose_frame, _RIGHT_SHOULDER_INDEX)
        return bool(
            (
                left_wrist is not None
                and left_shoulder is not None
                and left_wrist[1] < left_shoulder[1]
            )
            or (
                right_wrist is not None
                and right_shoulder is not None
                and right_wrist[1] < right_shoulder[1]
            )
        )

    def _landmark_xy(self, pose_frame: PoseFrame, index: int) -> tuple[float, float] | None:
        if index >= len(pose_frame.landmarks):
            return None
        landmark = pose_frame.landmarks[index]
        return (landmark.x, landmark.y)

    def _midpoint(
        self, pose_frame: PoseFrame, first_index: int, second_index: int
    ) -> tuple[float, float] | None:
        first = self._landmark_xy(pose_frame, first_index)
        second = self._landmark_xy(pose_frame, second_index)
        if first is None or second is None:
            return None
        return ((first[0] + second[0]) / 2, (first[1] + second[1]) / 2)

    def _rounded_average(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _optional_float(self, value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    def _stance_note(self, mechanics: PoseMechanicsMetrics, sample_count: int) -> str:
        if sample_count == 0:
            return "Pose samples were unavailable for the selected player."
        stance_width = mechanics.stance_width_ratio
        if stance_width is None:
            return "Stance width could not be measured reliably from the pose samples."
        if stance_width < 1.2:
            return "Stance width narrows slightly on late forehand recoveries."
        if stance_width > 1.7:
            return (
                "Base stance runs wide, which helps coverage but can slow the first recovery push."
            )
        return (
            "Base stance stays wide enough to load cleanly without overreaching between contacts."
        )

    def _preparation_note(self, mechanics: PoseMechanicsMetrics, sample_count: int) -> str:
        if sample_count == 0:
            return "Pose samples were unavailable for the selected player."
        preparation_rate = mechanics.preparation_rate
        if preparation_rate is None:
            return "Preparation timing could not be measured reliably from the pose samples."
        if preparation_rate < 0.35:
            return (
                "Racket-side preparation arrives late, so the upper body still looks "
                "rushed into contact."
            )
        if preparation_rate > 0.7:
            return (
                "Preparation starts early on balanced interceptions, which keeps the "
                "contact window stable."
            )
        return (
            "Preparation timing is playable, but the racket side still rises late on "
            "some deeper movements."
        )

    def _balance_note(self, mechanics: PoseMechanicsMetrics, sample_count: int) -> str:
        if sample_count == 0:
            return "Pose samples were unavailable for the selected player."
        balance_offset = mechanics.balance_offset_ratio
        trunk_lean = mechanics.trunk_lean_degrees
        if balance_offset is None or trunk_lean is None:
            return "Balance could not be measured reliably from the pose samples."
        if balance_offset > 0.35 or trunk_lean > 12:
            return "Balance drops when the final recovery hop lands too upright."
        return "Balance stays centered over the base well enough to support clean recovery steps."

    def _recovery_note(self, mechanics: PoseMechanicsMetrics, sample_count: int) -> str:
        if sample_count == 0:
            return "Pose samples were unavailable for the selected player."
        knee_flexion = mechanics.knee_flexion_degrees
        trunk_lean = mechanics.trunk_lean_degrees
        if knee_flexion is None or trunk_lean is None:
            return "Recovery timing could not be measured reliably from the pose samples."
        if knee_flexion > 155 or trunk_lean > 10:
            return "Recovery timing is playable but still late after deeper exits."
        return (
            "Recovery shape stays compact enough to reload quickly after most directional changes."
        )

    def _stroke_execution_note(self, mechanics: PoseMechanicsMetrics, sample_count: int) -> str:
        if sample_count == 0:
            return "Pose samples were unavailable for the selected player."
        balance_offset = mechanics.balance_offset_ratio
        preparation_rate = mechanics.preparation_rate
        if balance_offset is None or preparation_rate is None:
            return "Stroke execution quality could not be measured reliably from the pose samples."
        if balance_offset > 0.35 or preparation_rate < 0.35:
            return "Stroke execution quality falls off after off-balance contacts."
        return (
            "Stroke execution stays more repeatable when the body is loaded before the "
            "racket accelerates."
        )

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

    def _summarize_track(
        self,
        track_id: str,
        samples: list[TrackSample],
        court: CourtModel,
        match_type: MatchType,
    ) -> PlayerTrackSummary:
        homography = build_court_homography(court, match_type)
        projected = summarize_projected_track(samples, homography)
        distance = projected.total_distance_meters
        change_of_direction_count = 0
        burst_count = 0
        left_weight = 0.0
        right_weight = 0.0
        zone_counts = {"front": 0, "mid": 0, "rear": 0}
        last_dx: float | None = None

        for previous, current in zip(samples, samples[1:], strict=False):
            dx = current.x - previous.x
            dy = current.y - previous.y
            if last_dx is not None and (dx > 0 > last_dx or dx < 0 < last_dx):
                change_of_direction_count += 1
            if (dx * dx + dy * dy) ** 0.5 > 0.08:
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
            yolo_model=yolo_model or "yolo26n.pt",
            tracking_sample_fps=tracking_sample_fps or 2.0,
        )
    return MockCVPipeline()
