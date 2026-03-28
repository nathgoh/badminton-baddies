import uuid

from fastapi import APIRouter, UploadFile

from models.schemas import UploadResponse
from services.storage import get_video_dir

router = APIRouter(prefix="/api")


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile):
    video_id = str(uuid.uuid4())
    video_dir = get_video_dir(video_id)
    file_path = video_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    return UploadResponse(video_id=video_id, filename=file.filename)
