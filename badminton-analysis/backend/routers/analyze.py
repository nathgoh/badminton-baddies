import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.schemas import (
    AnalyzeRequest, AnalyzeStartResponse, AnalysisStatus,
    AnalysisResult, BoundingBox
)
from services.analysis import compute_stats, render_annotated_video
from services.detection import detect_persons
from services.pose import estimate_pose
from services.storage import StorageBackend, get_storage
from services.tracking import track_person_in_frame

router = APIRouter(prefix="/api")

# In-memory storage for analysis status (in production, use Redis/DB)
_analysis_status = {}
_status_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=2)


class AnalysisJob(BaseModel):
    id: str
    status: str
    progress: float | None = None
    result: AnalysisResult | None = None


@router.post("/analyze", response_model=AnalyzeStartResponse)
async def start_analysis(
    request: AnalyzeRequest,
    storage: StorageBackend = Depends(get_storage),
):
    analysis_id = str(uuid.uuid4())

    with _status_lock:
        _analysis_status[analysis_id] = AnalysisJob(
            id=analysis_id,
            status="processing",
            progress=0.0
        )

    _executor.submit(_run_analysis, analysis_id, request, storage)

    return AnalyzeStartResponse(analysis_id=analysis_id, status="processing")


@router.get("/analyze/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str):
    with _status_lock:
        job = _analysis_status.get(analysis_id)
        if not job:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return AnalysisStatus(
            status=job.status,
            progress=job.progress
        )


@router.get("/analyze/{analysis_id}/results", response_model=AnalysisResult)
async def get_analysis_results(analysis_id: str):
    with _status_lock:
        job = _analysis_status.get(analysis_id)
        if not job:
            raise HTTPException(status_code=404, detail="Analysis not found")

        if job.status != "completed":
            raise HTTPException(status_code=400, detail="Analysis not completed")

        if not job.result:
            raise HTTPException(status_code=500, detail="Results not available")

        return job.result


def _run_analysis(analysis_id: str, request: AnalyzeRequest, storage: StorageBackend):
    """Background analysis job."""
    try:
        _update_progress(analysis_id, 0.1)

        video_dir = storage.get_video_dir(request.video_id)
        video_files = (
            list(video_dir.glob("*.mp4"))
            + list(video_dir.glob("*.avi"))
            + list(video_dir.glob("*.mov"))
        )
        if not video_files:
            raise Exception("Video not found")

        video_path = str(video_files[0])

        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        _update_progress(analysis_id, 0.2)

        frame_data = []
        tracked_boxes = []
        all_landmarks = []
        positions = []

        prev_box = request.person_bbox

        for frame_idx in range(0, min(frame_count, 300), 2):
            time_sec = frame_idx / fps

            frame, persons = detect_persons(video_path, frame_idx)
            current_box = track_person_in_frame(prev_box, persons)
            if current_box is None:
                if persons:
                    current_box = max(persons, key=lambda p: p.confidence)
                else:
                    break

            tracked_boxes.append(current_box)

            bbox = (current_box.x, current_box.y, current_box.width, current_box.height)
            landmarks = estimate_pose(frame, bbox)
            all_landmarks.append(landmarks)

            center_x = current_box.x + current_box.width / 2
            center_y = current_box.y + current_box.height / 2
            positions.append((center_x, center_y))

            frame_data.append({
                "time_sec": time_sec,
                "center_x": center_x,
                "center_y": center_y,
                "landmarks": landmarks
            })

            prev_box = current_box

            progress = 0.2 + 0.6 * (frame_idx / min(frame_count, 300))
            _update_progress(analysis_id, progress)

        _update_progress(analysis_id, 0.8)

        stats = compute_stats(frame_data, width, height)

        _update_progress(analysis_id, 0.9)

        analysis_dir = storage.get_analysis_dir(analysis_id)
        output_path = analysis_dir / "annotated_video.mp4"
        render_annotated_video(
            video_path,
            str(output_path),
            tracked_boxes,
            all_landmarks,
            positions
        )

        result = AnalysisResult(
            stats=stats,
            annotated_video_url=f"/api/video/analyses/{analysis_id}/annotated_video.mp4"
        )

        with _status_lock:
            job = _analysis_status.get(analysis_id)
            if job:
                job.status = "completed"
                job.progress = 1.0
                job.result = result

    except Exception as e:
        with _status_lock:
            job = _analysis_status.get(analysis_id)
            if job:
                job.status = "failed"
                job.progress = None


def _update_progress(analysis_id: str, progress: float):
    """Helper to update analysis progress."""
    with _status_lock:
        job = _analysis_status.get(analysis_id)
        if job:
            job.progress = progress
