# Large Video Upload — Design Spec

## Overview

Replace the existing single-request upload endpoint (which loads the entire file into memory) with a **tus-protocol resumable upload server**. This supports multi-GB video files over slow or unreliable connections, provides real upload progress, and introduces a `StorageBackend` abstraction that enables future migration to S3 or other cloud storage without changing any router code.

## Scope

- Support video files of several GB (full badminton game recordings)
- Resumable: if connection drops mid-upload, the client resumes from the last acknowledged byte
- Real upload progress in the frontend
- Storage abstraction layer decoupling I/O from routing logic
- Fix existing `ThreadPoolExecutor` per-request leak in `analyze.py`
- Remove old in-memory upload endpoint

## Architecture

```
frontend (tus-js-client)
    │  POST   /api/tus          ← create upload
    │  HEAD   /api/tus/{id}     ← get current offset (resume)
    │  PATCH  /api/tus/{id}     ← write chunk
    ▼
routers/tus.py
    │
    ▼
services/storage.py  (StorageBackend protocol)
    │
    ▼
LocalStorageBackend  (local filesystem — current)
    or
S3StorageBackend     (future)
```

No changes to `/api/detect`, `/api/analyze`, or `/api/video` — they all consume `video_id` which remains the same.

## Backend

### tus Server (`routers/tus.py`)

Implements the [tus 1.0.0](https://tus.io/protocols/resumable-upload) core protocol plus the Creation extension.

| Method | Path | Purpose |
|--------|------|---------|
| `OPTIONS` | `/api/tus` | Announce version, max size, supported extensions |
| `POST` | `/api/tus` | Create upload: generate `upload_id`, initialize state, return `Location` |
| `HEAD` | `/api/tus/{upload_id}` | Return `Upload-Offset` for resumption |
| `PATCH` | `/api/tus/{upload_id}` | Write chunk at offset; finalize when complete |

**POST response headers:**
- `Location: /api/tus/{upload_id}`
- `Upload-Offset: 0`
- `Tus-Resumable: 1.0.0`

**PATCH response on completion** (offset == total size):
- `X-Video-Id: {upload_id}` — signals the frontend the video is ready

**Upload state** (per upload, stored in `storage/uploads/{upload_id}/meta.json`):
```json
{
  "upload_id": "...",
  "filename": "game.mp4",
  "total_size": 2147483648,
  "offset": 0,
  "created_at": "2026-03-29T..."
}
```

Chunks are written to `storage/uploads/{upload_id}/data` using seek+write at the given offset. On finalize, `data` is moved to `storage/{upload_id}/{filename}` — the exact path the existing detect/analyze endpoints already expect.

### Storage Abstraction (`services/storage.py`)

`StorageBackend` is a `Protocol` (structural typing). All routers receive it via `Depends(get_storage)`.

```python
class StorageBackend(Protocol):
    def create_upload(self, upload_id: str, total_size: int, filename: str) -> None: ...
    def get_upload_meta(self, upload_id: str) -> dict: ...
    def write_chunk(self, upload_id: str, offset: int, data: bytes) -> int: ...  # returns new offset
    def finalize_upload(self, upload_id: str) -> None: ...
    def get_video_dir(self, video_id: str) -> Path: ...
    def get_video_path(self, video_id: str, filename: str) -> Path: ...
    def get_analysis_dir(self, analysis_id: str) -> Path: ...
```

`LocalStorageBackend` is the concrete implementation. It lives in the same file and is instantiated once at startup.

**Cloud migration path:** Implement `S3StorageBackend` where:
- `create_upload` → `s3.create_multipart_upload`
- `write_chunk` → `s3.upload_part`
- `finalize_upload` → `s3.complete_multipart_upload`

Swap the `get_storage` dependency — no router changes required.

### Fix: `analyze.py` executor leak

Move `ThreadPoolExecutor(max_workers=2)` to module level. Currently a new executor is created per request and never shut down.

### Removed: `routers/upload.py`

`POST /api/upload` is deleted. It loaded the full file into memory with `await file.read()`. tus is the only upload path.

## Frontend

### `tus-js-client` integration (`VideoUploader.tsx`)

Replace the `apiClient.uploadVideo(file)` call with a `tus.Upload` instance:

```ts
new tus.Upload(file, {
  endpoint: '/api/tus',
  chunkSize: 10 * 1024 * 1024,  // 10MB chunks
  retryDelays: [0, 1000, 3000, 5000],
  metadata: { filename: file.name, filetype: file.type },
  onProgress(bytesUploaded, bytesTotal) { /* real progress */ },
  onSuccess() { /* extract X-Video-Id, call onUploadSuccess */ },
  onError(err) { /* show error */ },
})
```

Built-in fingerprinting stores the upload URL in `localStorage` keyed by file identity. Re-selecting the same file after a connection drop automatically resumes.

File size label updated to "No size limit". No other UI changes.

### `api/client.ts`

Remove `uploadVideo()` method. All other methods unchanged.

## Files Changed

| File | Change |
|------|--------|
| `backend/routers/tus.py` | New — tus server endpoints |
| `backend/routers/upload.py` | Deleted |
| `backend/services/storage.py` | Rewritten — add `StorageBackend` protocol + `LocalStorageBackend` |
| `backend/main.py` | Register tus router, remove upload router |
| `backend/routers/detect.py` | Update storage import to use `Depends(get_storage)` |
| `backend/routers/video.py` | Update storage import to use `Depends(get_storage)` |
| `backend/routers/analyze.py` | Update storage import; fix executor leak |
| `frontend/src/components/VideoUploader.tsx` | Rewrite upload logic with tus-js-client |
| `frontend/src/api/client.ts` | Remove `uploadVideo()` |

## Assumptions

- tus 1.0.0 core + Creation extension is sufficient (no Concatenation or Checksum extensions needed)
- 10MB chunk size is appropriate for multi-GB files over typical connections
- Upload state survives server restarts (stored on disk, not in memory)
- Incomplete uploads in `storage/uploads/` can be cleaned up manually or by a future background job
