from __future__ import annotations

import os

from fastapi import FastAPI, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ..analyses.service import AnalysisService
from ..coaching.engine import build_coach_feedback_engine_from_env
from ..pipelines.cv.pipeline import build_cv_pipeline_from_env
from ..pipelines.media.pipeline import build_media_artifact_pipeline_from_env
from ..schemas import (
    AnalysisActionResponse,
    AnalysisCreateInput,
    AnalysisCreateResponse,
    AnalysisListResponse,
    AnalysisReport,
    AnalysisSelectionInput,
    AnalysisSetupResponse,
    AnalysisStatusResponse,
)


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


service = AnalysisService(
    coach_feedback_engine=build_coach_feedback_engine_from_env(
        engine_name=os.getenv("COACH_FEEDBACK_ENGINE"),
        provider=os.getenv("LLM_PROVIDER"),
        model=os.getenv("LLM_MODEL") or os.getenv("PYDANTIC_AI_MODEL"),
    ),
    media_artifact_pipeline=build_media_artifact_pipeline_from_env(
        mode=os.getenv("MEDIA_PIPELINE"),
        artifact_root=os.getenv("MEDIA_ARTIFACT_ROOT"),
    ),
    cv_pipeline=build_cv_pipeline_from_env(
        mode=os.getenv("CV_PIPELINE"),
        yolo_model=os.getenv("YOLO_MODEL"),
        tracking_sample_fps=_env_float("TRACKING_SAMPLE_FPS", 2.0),
    ),
)
app = FastAPI(title="Badminton Analysis API", version="0.1.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/analyses", response_model=AnalysisCreateResponse, status_code=status.HTTP_201_CREATED
)
def create_analysis(
    payload: AnalysisCreateInput,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisCreateResponse:
    return service.create_analysis(payload, owner_id=owner_id)


@app.get("/api/analyses", response_model=AnalysisListResponse)
def list_analyses(
    page: int = 1,
    page_size: int = 20,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisListResponse:
    page_size = min(page_size, 100)
    return service.list_analyses(page=page, page_size=page_size, owner_id=owner_id)


@app.get("/api/analyses/{analysis_id}/setup", response_model=AnalysisSetupResponse)
def get_setup(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisSetupResponse:
    return service.get_setup(analysis_id, owner_id=owner_id)


@app.get("/api/analyses/{analysis_id}/setup-frame")
def get_setup_frame(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> FileResponse:
    path, media_type = service.get_setup_frame_file(analysis_id, owner_id=owner_id)
    return FileResponse(path, media_type=media_type)


@app.post(
    "/api/analyses/{analysis_id}/selection",
    response_model=AnalysisActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def apply_selection(
    analysis_id: str,
    payload: AnalysisSelectionInput,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisActionResponse:
    return service.apply_selection(analysis_id, payload, owner_id=owner_id)


@app.post(
    "/api/analyses/{analysis_id}/run",
    response_model=AnalysisActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_analysis(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisActionResponse:
    return service.run_analysis(analysis_id, owner_id=owner_id)


@app.get("/api/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_status(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisStatusResponse:
    return service.get_status(analysis_id, owner_id=owner_id)


@app.get("/api/analyses/{analysis_id}/report", response_model=AnalysisReport)
def get_report(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> AnalysisReport:
    return service.get_report(analysis_id, owner_id=owner_id)


@app.delete("/api/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: str,
    owner_id: str | None = Header(default=None, alias="X-Owner-Id"),
) -> None:
    service.delete_analysis(analysis_id, owner_id=owner_id)
