from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.storage import get_video_path

router = APIRouter(prefix="/api")


@router.get("/video/{video_id}/{filename}")
async def serve_video(video_id: str, filename: str):
    path = get_video_path(video_id, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")
