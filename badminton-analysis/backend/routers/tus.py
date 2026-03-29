import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from services.storage import LocalStorageBackend, get_storage

router = APIRouter(prefix="/api/tus")

TUS_VERSION = "1.0.0"
TUS_MAX_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB


@router.options("")
async def tus_options() -> Response:
    return Response(
        status_code=204,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Tus-Version": TUS_VERSION,
            "Tus-Max-Size": str(TUS_MAX_SIZE),
            "Tus-Extension": "creation",
        },
    )


@router.post("")
async def tus_create(
    request: Request,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    upload_length = request.headers.get("Upload-Length")
    if not upload_length:
        raise HTTPException(status_code=400, detail="Upload-Length header required")

    total_size = int(upload_length)
    if total_size > TUS_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    filename = "upload"
    for part in request.headers.get("Upload-Metadata", "").split(","):
        part = part.strip()
        if part.startswith("filename "):
            filename = base64.b64decode(part[len("filename "):]).decode("utf-8")
            break

    upload_id = str(uuid.uuid4())
    storage.create_upload(upload_id, total_size, filename)

    return Response(
        status_code=201,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Location": f"/api/tus/{upload_id}",
            "Upload-Offset": "0",
        },
    )


@router.head("/{upload_id}")
async def tus_head(
    upload_id: str,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    try:
        meta = storage.get_upload_meta(upload_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")

    return Response(
        status_code=200,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Upload-Offset": str(meta["offset"]),
            "Upload-Length": str(meta["total_size"]),
            "Cache-Control": "no-store",
        },
    )


@router.patch("/{upload_id}")
async def tus_patch(
    upload_id: str,
    request: Request,
    storage: LocalStorageBackend = Depends(get_storage),
) -> Response:
    if request.headers.get("Content-Type") != "application/offset+octet-stream":
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/offset+octet-stream",
        )

    upload_offset = request.headers.get("Upload-Offset")
    if upload_offset is None:
        raise HTTPException(status_code=400, detail="Upload-Offset header required")

    offset = int(upload_offset)

    try:
        meta = storage.get_upload_meta(upload_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload not found")

    if meta["offset"] != offset:
        raise HTTPException(
            status_code=409,
            detail=f"Offset mismatch: expected {meta['offset']}, got {offset}",
        )

    data = await request.body()
    new_offset = storage.write_chunk(upload_id, offset, data)

    headers = {
        "Tus-Resumable": TUS_VERSION,
        "Upload-Offset": str(new_offset),
    }

    if new_offset == meta["total_size"]:
        storage.finalize_upload(upload_id)
        headers["X-Video-Id"] = upload_id

    return Response(status_code=204, headers=headers)
