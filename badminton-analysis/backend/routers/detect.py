import base64

import cv2
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import DetectRequest, DetectResponse
from services.detection import detect_persons
from services.storage import StorageBackend, get_storage

router = APIRouter(prefix="/api")


@router.post("/detect", response_model=DetectResponse)
async def detect(
    request: DetectRequest,
    storage: StorageBackend = Depends(get_storage),
):
    video_dir = storage.get_video_dir(request.video_id)
    video_files = (
        list(video_dir.glob("*.mp4"))
        + list(video_dir.glob("*.avi"))
        + list(video_dir.glob("*.mov"))
    )
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(video_files[0])
    frame, persons = detect_persons(video_path, request.frame_number)

    _, buffer = cv2.imencode(".jpg", frame)
    frame_b64 = base64.b64encode(buffer).decode("utf-8")

    return DetectResponse(frame_image=frame_b64, persons=persons)
