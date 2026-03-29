from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.storage import get_video_path, get_analysis_dir

router = APIRouter(prefix="/api")


@router.get("/video/{video_id}/{filename}")
async def serve_video(video_id: str, filename: str):
    path = get_video_path(video_id, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/video/analyses/{analysis_id}/{filename}")
async def serve_analysis_video(analysis_id: str, filename: str):
    analysis_dir = get_analysis_dir(analysis_id)
    path = analysis_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis video not found")
    return FileResponse(path, media_type="video/mp4")
