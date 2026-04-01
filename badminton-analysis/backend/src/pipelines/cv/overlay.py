from __future__ import annotations

from typing import Any

from schemas import DetectionBox

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

POSE_CONNECTIONS = (
    (_LEFT_SHOULDER_INDEX, _RIGHT_SHOULDER_INDEX),
    (_LEFT_SHOULDER_INDEX, _LEFT_ELBOW_INDEX),
    (_LEFT_ELBOW_INDEX, _LEFT_WRIST_INDEX),
    (_RIGHT_SHOULDER_INDEX, _RIGHT_ELBOW_INDEX),
    (_RIGHT_ELBOW_INDEX, _RIGHT_WRIST_INDEX),
    (_LEFT_SHOULDER_INDEX, _LEFT_HIP_INDEX),
    (_RIGHT_SHOULDER_INDEX, _RIGHT_HIP_INDEX),
    (_LEFT_HIP_INDEX, _RIGHT_HIP_INDEX),
    (_LEFT_HIP_INDEX, _LEFT_KNEE_INDEX),
    (_LEFT_KNEE_INDEX, _LEFT_ANKLE_INDEX),
    (_RIGHT_HIP_INDEX, _RIGHT_KNEE_INDEX),
    (_RIGHT_KNEE_INDEX, _RIGHT_ANKLE_INDEX),
)


def draw_player_pose_overlay(
    cv2: Any,
    frame: Any,
    *,
    box: DetectionBox | None,
    poses: list[list[Any]] | None,
) -> Any:
    annotated = frame
    height, width = annotated.shape[:2]
    if box is not None:
        x1 = int(box.x * width)
        y1 = int(box.y * height)
        x2 = int((box.x + box.width) * width)
        y2 = int((box.y + box.height) * height)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 165, 0), 2)
    if poses:
        for pose in poses:
            for start_index, end_index in POSE_CONNECTIONS:
                if len(pose) <= max(start_index, end_index):
                    continue
                start = pose[start_index]
                end = pose[end_index]
                cv2.line(
                    annotated,
                    (int(start.x * width), int(start.y * height)),
                    (int(end.x * width), int(end.y * height)),
                    (64, 224, 208),
                    2,
                )
            for landmark in pose:
                cv2.circle(
                    annotated,
                    (int(landmark.x * width), int(landmark.y * height)),
                    3,
                    (0, 0, 255),
                    -1,
                )
    return annotated
