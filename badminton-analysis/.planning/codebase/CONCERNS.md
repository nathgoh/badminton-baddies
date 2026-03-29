# CONCERNS.md — Technical Debt, Bugs, Security, Performance

## Tech Debt

### Critical / Blocking Features
- **`services/pose.py` is a stub** — returns `None`; pose estimation is entirely unimplemented despite being a declared feature
- **Skeleton drawing key mismatch** — `_draw_skeleton` uses `"LANDMARK_N"` key format but landmarks are named `"RIGHT_WRIST"` etc.; skeleton overlay never renders

### Architecture / Reliability
- **In-memory analysis job store** — `_analysis_status` dict in `routers/analyze.py` is process-local; state lost on restart, incompatible with multi-worker deployments
- **Dual upload paths** — `routers/upload.py` (legacy `POST /api/upload`) and `routers/tus.py` (resumable TUS protocol) coexist with backwards-compat shims in `services/storage.py`; long-term one path should be removed

### Hard-coded Assumptions
- **`frame_height = 13.4m`** pixel-to-meter conversion in `services/analysis.py` — hard-coded court dimension; breaks for any non-standard video framing

### Performance
- **Per-frame VideoCapture open/close** — analysis loop opens and closes `cv2.VideoCapture` once per frame (~150 open/close cycles per video); should be opened once and seeked

## Security

### Input Validation
- **No file type validation** on either upload endpoint (`/api/upload` and TUS) — any file type accepted
- **No server-side file size limit** on legacy `POST /api/upload`

### Path Traversal
- **TUS upload metadata `filename` not sanitized** — `../` sequences not stripped; attacker can write files outside upload directory
- **`filename` path parameter in video serving endpoints** not sanitized — same path traversal risk

### CORS
- **`allow_methods=["*"]` and `allow_headers=["*"]`** — overly permissive CORS configuration

## Test Coverage Gaps

- **`_run_analysis` background function** — never tested end-to-end; the core analysis pipeline has no integration test
- **`render_annotated_video` and `_draw_skeleton`** — untested; skeleton bug (key mismatch above) is undetected because of this
- **Frontend has zero automated tests**
- **`SelectPage.tsx`** hardcodes 640×480 for bounding box overlay calculations — will break for other resolutions

## Fragile Areas

| Area | File | Risk |
|------|------|------|
| Pose estimation stub | `services/pose.py` | Returns `None` silently; callers may not handle `None` |
| Job state store | `routers/analyze.py` | In-memory dict; no persistence |
| TUS metadata parsing | `routers/tus.py` | Filename not sanitized before path join |
| Analysis pixel math | `services/analysis.py` | Hard-coded court height assumption |
| Skeleton rendering | `services/analysis.py` | Key name mismatch — skeleton never drawn |
| VideoCapture lifecycle | `services/analysis.py` | Opened per-frame; resource-intensive |

## Known Issues / TODOs

- Pose estimation (the core product feature) is unimplemented
- Skeleton overlay is broken due to landmark key naming mismatch
- Upload cleanup (orphaned files) is not handled
- No rate limiting on any endpoint
