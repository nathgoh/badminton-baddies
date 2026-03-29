import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import (
    AnalyzeRequest, AnalyzeStartResponse, AnalysisStatus, 
    AnalysisResult, BoundingBox
)
from services.storage import get_video_dir, get_analysis_dir
from services.analysis import compute_stats, render_annotated_video
from services.detection import detect_persons
from services.tracking import track_person_in_frame
from services.pose import estimate_pose

router = APIRouter(prefix="/api")

# In-memory storage for analysis status (in production, use Redis/DB)
_analysis_status = {}
_status_lock = Lock()


class AnalysisJob(BaseModel):
    id: str
    status: str
    progress: float | None = None
    result: AnalysisResult | None = None


@router.post("/analyze", response_model=AnalyzeStartResponse)
async def start_analysis(request: AnalyzeRequest):
    analysis_id = str(uuid.uuid4())
    
    # Store initial status
    with _status_lock:
        _analysis_status[analysis_id] = AnalysisJob(
            id=analysis_id,
            status="processing",
            progress=0.0
        )
    
    # Run analysis in background
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(_run_analysis, analysis_id, request)
    
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


def _run_analysis(analysis_id: str, request: AnalyzeRequest):
    """Background analysis job."""
    try:
        # Update progress
        _update_progress(analysis_id, 0.1)
        
        # Get video path
        video_dir = get_video_dir(request.video_id)
        video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.avi")) + list(video_dir.glob("*.mov"))
        if not video_files:
            raise Exception("Video not found")
        
        video_path = str(video_files[0])
        
        # Open video to get properties
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        _update_progress(analysis_id, 0.2)
        
        # Track person across frames and extract pose
        frame_data = []
        tracked_boxes = []
        all_landmarks = []
        positions = []
        
        prev_box = request.person_bbox
        
        for frame_idx in range(0, min(frame_count, 300), 2):  # Limit to 300 frames, sample every 2nd
            time_sec = frame_idx / fps
            
            # Detect persons in frame
            frame, persons = detect_persons(video_path, frame_idx)
            
            # Track the selected person
            current_box = track_person_in_frame(prev_box, persons)
            if current_box is None:
                # Try to find the best match by confidence
                if persons:
                    current_box = max(persons, key=lambda p: p.confidence)
                else:
                    break  # No persons detected
            
            tracked_boxes.append(current_box)
            
            # Extract pose
            bbox = (current_box.x, current_box.y, current_box.width, current_box.height)
            landmarks = estimate_pose(frame, bbox)
            all_landmarks.append(landmarks)
            
            # Calculate center position
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
            
            # Update progress
            progress = 0.2 + 0.6 * (frame_idx / min(frame_count, 300))
            _update_progress(analysis_id, progress)
        
        _update_progress(analysis_id, 0.8)
        
        # Compute stats
        stats = compute_stats(frame_data, width, height)
        
        _update_progress(analysis_id, 0.9)
        
        # Render annotated video
        analysis_dir = get_analysis_dir(analysis_id)
        output_path = analysis_dir / "annotated_video.mp4"
        render_annotated_video(
            video_path, 
            str(output_path), 
            tracked_boxes, 
            all_landmarks, 
            positions
        )
        
        # Create result
        result = AnalysisResult(
            stats=stats,
            annotated_video_url=f"/api/video/analyses/{analysis_id}/annotated_video.mp4"
        )
        
        # Update final status
        with _status_lock:
            job = _analysis_status.get(analysis_id)
            if job:
                job.status = "completed"
                job.progress = 1.0
                job.result = result
                
    except Exception as e:
        # Update status to failed
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
