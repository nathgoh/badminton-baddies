from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

import pipelines.cv.pipeline as pipeline_module
from schemas import DetectionBox, PlayerTrackSummary, TrackSample


class _FakeCapture:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = frames
        self._current_index = 0

    def isOpened(self) -> bool:
        return True

    def set(self, prop: int, value: int) -> None:
        if prop == 1:
            self._current_index = int(value)

    def read(self) -> tuple[bool, np.ndarray | None]:
        if 0 <= self._current_index < len(self._frames):
            return True, self._frames[self._current_index]
        return False, None

    def release(self) -> None:
        return None


class _FakeCV2:
    CAP_PROP_POS_FRAMES = 1
    CAP_PROP_FPS = 5
    COLOR_BGR2RGB = 10

    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = frames

    def VideoCapture(self, _: str) -> _FakeCapture:
        return _FakeCapture(self._frames)

    def cvtColor(self, frame: np.ndarray, _: int) -> np.ndarray:
        return frame


class _FakeDrawCV2:
    IMWRITE_JPEG_QUALITY = 1

    def __init__(self) -> None:
        self.lines: list[tuple[tuple[int, int], tuple[int, int]]] = []
        self.circles: list[tuple[int, int]] = []
        self.rectangles: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def rectangle(
        self,
        _image: np.ndarray,
        start: tuple[int, int],
        end: tuple[int, int],
        _color: tuple[int, int, int],
        _thickness: int,
    ) -> None:
        self.rectangles.append((start, end))

    def line(
        self,
        _image: np.ndarray,
        start: tuple[int, int],
        end: tuple[int, int],
        _color: tuple[int, int, int],
        _thickness: int,
    ) -> None:
        self.lines.append((start, end))

    def circle(
        self,
        _image: np.ndarray,
        center: tuple[int, int],
        _radius: int,
        _color: tuple[int, int, int],
        _thickness: int,
    ) -> None:
        self.circles.append(center)

    def imencode(
        self, _extension: str, _image: np.ndarray, _params: list[int]
    ) -> tuple[bool, np.ndarray]:
        return True, np.array([1, 2, 3], dtype=np.uint8)


def test_extract_pose_crops_frame_to_bounding_box(monkeypatch) -> None:
    frames = [np.zeros((120, 200, 3), dtype=np.uint8) for _ in range(3)]
    fake_cv2 = _FakeCV2(frames)
    detect_calls: list[np.ndarray] = []

    class FakeImage:
        def __init__(self, *, image_format: object, data: np.ndarray) -> None:
            self.image_format = image_format
            self.data = data

    class FakeLandmarker:
        def detect(self, image: FakeImage):
            detect_calls.append(image.data)
            return SimpleNamespace(pose_landmarks=[[object()]])

        def close(self) -> None:
            return None

    fake_mp = SimpleNamespace(
        Image=FakeImage,
        ImageFormat=SimpleNamespace(SRGB="srgb"),
        tasks=SimpleNamespace(
            BaseOptions=lambda **kwargs: SimpleNamespace(**kwargs),
            vision=SimpleNamespace(
                RunningMode=SimpleNamespace(IMAGE="image"),
                PoseLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
                PoseLandmarker=SimpleNamespace(
                    create_from_options=lambda options: FakeLandmarker()
                ),
            ),
            components=SimpleNamespace(
                containers=SimpleNamespace(RectF=lambda **kwargs: SimpleNamespace(**kwargs))
            ),
        ),
    )

    def fake_import_module(name: str):
        if name == "cv2":
            return fake_cv2
        if name == "mediapipe":
            return fake_mp
        raise AssertionError(f"Unexpected import {name}")

    monkeypatch.setattr(pipeline_module, "import_module", fake_import_module)
    monkeypatch.setattr(
        pipeline_module.HybridCVPipeline,
        "_ensure_pose_model",
        lambda self: Path("/tmp/fake-pose.task"),
    )

    pipeline = pipeline_module.HybridCVPipeline()
    # box: x=0.2, y=0.25, w=0.3, h=0.5 on a 200x120 frame
    # expected crop: x1=40, y1=30, x2=100, y2=90 → 60x60 pixels
    selected_track = PlayerTrackSummary(
        track_id="track-1",
        source_player_id="player-1",
        total_distance_meters=12.3,
        recovery_score=74,
        court_coverage_percent=81,
        change_of_direction_count=8,
        burst_count=2,
        directional_balance={"left": 0.48, "right": 0.52},
        zone_occupancy={"front": 20, "mid": 45, "rear": 35},
        heatmap=[],
        samples=[
            TrackSample(
                frame_index=0,
                timestamp_seconds=0.0,
                x=0.31,
                y=0.72,
                bounding_box=DetectionBox(x=0.2, y=0.25, width=0.3, height=0.5),
            ),
            TrackSample(
                frame_index=1,
                timestamp_seconds=0.2,
                x=0.33,
                y=0.7,
                bounding_box=DetectionBox(x=0.2, y=0.25, width=0.3, height=0.5),
            ),
            TrackSample(
                frame_index=2,
                timestamp_seconds=0.4,
                x=0.35,
                y=0.68,
                bounding_box=DetectionBox(x=0.2, y=0.25, width=0.3, height=0.5),
            ),
        ],
    )

    pipeline.extract_pose("fake-video.mp4", selected_track)

    assert len(detect_calls) == 3
    # Cropped frame should be 60x60 (not the full 120x200)
    assert detect_calls[0].shape == (60, 60, 3)


def test_extract_pose_returns_pose_frames_and_mechanics_metrics(monkeypatch) -> None:
    frames = [np.zeros((120, 200, 3), dtype=np.uint8) for _ in range(2)]
    fake_cv2 = _FakeCV2(frames)

    def make_landmarks(offset: float):
        points = [SimpleNamespace(x=0.0, y=0.0, z=0.0, visibility=0.0) for _ in range(33)]
        points[0] = SimpleNamespace(x=0.35 + offset, y=0.2, z=0.0, visibility=0.99)  # nose
        points[11] = SimpleNamespace(x=0.3, y=0.3, z=0.0, visibility=0.99)  # left shoulder
        points[12] = SimpleNamespace(x=0.45, y=0.3, z=0.0, visibility=0.99)  # right shoulder
        points[15] = SimpleNamespace(x=0.28, y=0.22, z=0.0, visibility=0.99)  # left wrist
        points[16] = SimpleNamespace(x=0.47, y=0.21, z=0.0, visibility=0.99)  # right wrist
        points[23] = SimpleNamespace(x=0.33, y=0.5, z=0.0, visibility=0.99)  # left hip
        points[24] = SimpleNamespace(x=0.42, y=0.5, z=0.0, visibility=0.99)  # right hip
        points[25] = SimpleNamespace(x=0.31, y=0.68, z=0.0, visibility=0.99)  # left knee
        points[26] = SimpleNamespace(x=0.44, y=0.68, z=0.0, visibility=0.99)  # right knee
        points[27] = SimpleNamespace(x=0.24, y=0.89, z=0.0, visibility=0.99)  # left ankle
        points[28] = SimpleNamespace(x=0.52, y=0.89, z=0.0, visibility=0.99)  # right ankle
        return points

    landmark_frames = [make_landmarks(0.0), make_landmarks(0.02)]

    class FakeImage:
        def __init__(self, *, image_format: object, data: np.ndarray) -> None:
            self.image_format = image_format
            self.data = data

    class FakeLandmarker:
        def __init__(self) -> None:
            self._index = 0

        def detect(self, image: FakeImage):
            current = landmark_frames[self._index]
            self._index += 1
            return SimpleNamespace(pose_landmarks=[current])

        def close(self) -> None:
            return None

    fake_mp = SimpleNamespace(
        Image=FakeImage,
        ImageFormat=SimpleNamespace(SRGB="srgb"),
        tasks=SimpleNamespace(
            BaseOptions=lambda **kwargs: SimpleNamespace(**kwargs),
            vision=SimpleNamespace(
                RunningMode=SimpleNamespace(IMAGE="image"),
                PoseLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
                PoseLandmarker=SimpleNamespace(
                    create_from_options=lambda options: FakeLandmarker()
                ),
                ImageProcessingOptions=lambda **kwargs: SimpleNamespace(**kwargs),
            ),
            components=SimpleNamespace(
                containers=SimpleNamespace(RectF=lambda **kwargs: SimpleNamespace(**kwargs))
            ),
        ),
    )

    def fake_import_module(name: str):
        if name == "cv2":
            return fake_cv2
        if name == "mediapipe":
            return fake_mp
        raise AssertionError(f"Unexpected import {name}")

    monkeypatch.setattr(pipeline_module, "import_module", fake_import_module)
    monkeypatch.setattr(
        pipeline_module.HybridCVPipeline,
        "_ensure_pose_model",
        lambda self: Path("/tmp/fake-pose.task"),
    )

    pipeline = pipeline_module.HybridCVPipeline()
    selected_track = PlayerTrackSummary(
        track_id="track-1",
        source_player_id="player-1",
        total_distance_meters=12.3,
        recovery_score=74,
        court_coverage_percent=81,
        change_of_direction_count=8,
        burst_count=2,
        directional_balance={"left": 0.48, "right": 0.52},
        zone_occupancy={"front": 20, "mid": 45, "rear": 35},
        heatmap=[],
        samples=[
            TrackSample(
                frame_index=0,
                timestamp_seconds=0.0,
                x=0.31,
                y=0.72,
                bounding_box=DetectionBox(x=0.2, y=0.25, width=0.3, height=0.5),
            ),
            TrackSample(
                frame_index=1,
                timestamp_seconds=0.2,
                x=0.33,
                y=0.7,
                bounding_box=DetectionBox(x=0.2, y=0.25, width=0.3, height=0.5),
            ),
        ],
    )

    summary = pipeline.extract_pose("fake-video.mp4", selected_track)

    assert summary.sample_count == 2
    assert len(summary.pose_frames) == 2
    assert len(summary.pose_frames[0].landmarks) == 33
    assert summary.mechanics.stance_width_ratio is not None
    assert summary.mechanics.knee_flexion_degrees is not None
    assert summary.mechanics.trunk_lean_degrees is not None
    assert summary.mechanics.balance_offset_ratio is not None
    assert summary.mechanics.preparation_rate is not None


def test_annotate_pose_draws_skeleton_connections() -> None:
    draw_cv2 = _FakeDrawCV2()
    pipeline = pipeline_module.HybridCVPipeline()
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    pose = [SimpleNamespace(x=0.3, y=0.3), SimpleNamespace(x=0.6, y=0.3)]

    jpeg = pipeline._annotate_pose(
        draw_cv2,
        frame,
        [
            [
                *([SimpleNamespace(x=0.0, y=0.0) for _ in range(11)]),
                pose[0],
                pose[1],
            ]
        ],
        DetectionBox(x=0.2, y=0.2, width=0.4, height=0.5),
    )

    assert jpeg == b"\x01\x02\x03"
    assert draw_cv2.rectangles
    assert draw_cv2.circles
    assert draw_cv2.lines
