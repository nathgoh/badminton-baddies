import cv2
import numpy as np
from ultralytics import YOLO

from models.schemas import BoundingBox

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
    return _model


def extract_frame(video_path: str, frame_number: int = 0) -> np.ndarray | None:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame


def detect_persons(video_path: str, frame_number: int = 0) -> tuple[np.ndarray, list[BoundingBox]]:
    frame = extract_frame(video_path, frame_number)
    if frame is None:
        raise ValueError("Could not read frame from video")

    model = _get_model()
    results = model(frame, verbose=False)

    persons = []
    for i, box in enumerate(results[0].boxes):
        cls = int(box.cls[0])
        if cls != 0:  # 0 = person class in COCO
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        persons.append(BoundingBox(
            id=i,
            x=x1,
            y=y1,
            width=x2 - x1,
            height=y2 - y1,
            confidence=conf,
        ))

    return frame, persons
