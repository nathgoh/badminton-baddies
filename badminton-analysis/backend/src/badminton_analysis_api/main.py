from __future__ import annotations

import os

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AnalysisActionResponse,
    AnalysisCreateInput,
    AnalysisCreateResponse,
    AnalysisListResponse,
    AnalysisReport,
    AnalysisSelectionInput,
    AnalysisSetupResponse,
    AnalysisStatusResponse,
)
from .service import AnalysisService

service = AnalysisService()
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
def create_analysis(payload: AnalysisCreateInput) -> AnalysisCreateResponse:
    return service.create_analysis(payload)


@app.get("/api/analyses", response_model=AnalysisListResponse)
def list_analyses(page: int = 1, page_size: int = 20) -> AnalysisListResponse:
    page_size = min(page_size, 100)
    return service.list_analyses(page=page, page_size=page_size)


@app.get("/api/analyses/{analysis_id}/setup", response_model=AnalysisSetupResponse)
def get_setup(analysis_id: str) -> AnalysisSetupResponse:
    return service.get_setup(analysis_id)


@app.post(
    "/api/analyses/{analysis_id}/selection",
    response_model=AnalysisActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def apply_selection(
    analysis_id: str,
    payload: AnalysisSelectionInput,
) -> AnalysisActionResponse:
    return service.apply_selection(analysis_id, payload)


@app.post(
    "/api/analyses/{analysis_id}/run",
    response_model=AnalysisActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_analysis(analysis_id: str) -> AnalysisActionResponse:
    return service.run_analysis(analysis_id)


@app.get("/api/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_status(analysis_id: str) -> AnalysisStatusResponse:
    return service.get_status(analysis_id)


@app.get("/api/analyses/{analysis_id}/report", response_model=AnalysisReport)
def get_report(analysis_id: str) -> AnalysisReport:
    return service.get_report(analysis_id)


@app.delete("/api/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: str) -> None:
    service.delete_analysis(analysis_id)
