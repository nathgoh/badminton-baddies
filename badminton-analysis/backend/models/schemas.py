from pydantic import BaseModel


class UploadResponse(BaseModel):
    video_id: str
    filename: str


class BoundingBox(BaseModel):
    id: int
    x: float
    y: float
    width: float
    height: float
    confidence: float


class DetectRequest(BaseModel):
    video_id: str
    frame_number: int = 0


class DetectResponse(BaseModel):
    frame_image: str
    persons: list[BoundingBox]


class AnalyzeRequest(BaseModel):
    video_id: str
    person_bbox: BoundingBox


class AnalyzeStartResponse(BaseModel):
    analysis_id: str
    status: str = "processing"


class AnalysisStatus(BaseModel):
    status: str
    progress: float | None = None


class MovementPoint(BaseModel):
    time_sec: float
    distance: float


class AnalysisStats(BaseModel):
    total_distance_meters: float
    avg_speed_mps: float
    court_coverage_pct: float
    estimated_shot_count: int
    movement_over_time: list[MovementPoint]


class AnalysisResult(BaseModel):
    stats: AnalysisStats
    annotated_video_url: str
