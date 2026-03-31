# Implementation Analysis: Badminton Analysis

## 1. Core Architectural Issues

### A. "Poll-to-Progress" Anti-pattern
The current implementation of `AnalysisService._advance_analysis` increments progress based on client `GET /api/analyses/{id}/status` requests.
- **Problem:** If a user doesn't poll, the analysis never finishes. If a user polls rapidly, it "finishes" instantly but then blocks the final poll request while performing the *actual* heavy CV work synchronously in `_complete_analysis`.
- **Suggestion:** Use FastAPI's `BackgroundTasks` or a task queue (like Celery or RQ). The `POST /run` endpoint should trigger the background task, and the background task should update the record in the store as it reaches real milestones.

### B. Synchronous Processing of Heavy Tasks
The `HybridCVPipeline` methods (`track_players`, `extract_pose`) are CPU/GPU intensive.
- **Problem:** Running these inside a FastAPI request handler will lead to timeouts and block the event loop if not handled correctly (though FastAPI runs sync routes in a threadpool, it's still inefficient for long-running CV tasks).
- **Suggestion:** Offload CV processing to a dedicated worker process.

### C. Transient Storage
The `AnalysisStore` is a simple `dict`.
- **Problem:** All data is lost on server restart. Media artifacts in `/tmp` might persist longer than the in-memory records, leading to orphaned files.
- **Suggestion:** Implement a SQL-based store using SQLAlchemy or SQLModel with SQLite for local development and PostgreSQL for production.

## 2. Frontend Implementation

### A. Single-File Component (`App.tsx`)
The entire application logic, state, and UI are in one 600+ line file.
- **Problem:** Hard to maintain, test, and reason about.
- **Suggestion:** Componentize the UI:
  - `WorkflowStepper` (The progress indicator)
  - `AnalyzeScreen` (URL input and match type)
  - `SetupScreen` (Court adjustment and player selection)
  - `ProcessingScreen` (Progress bar and status messages)
  - `ReportView` (The final two-tab report)

### B. State Management
The state is managed via many `useState` hooks in the root component.
- **Problem:** Prop drilling and difficulty in managing complex transitions.
- **Suggestion:** Use a reducer (`useReducer`) for the screen state machine or a lightweight state library like Zustand.

## 3. Media & CV Pipelines

### A. Media Pipeline Robustness
The `ShellMediaArtifactPipeline` uses `subprocess.run` to call `yt-dlp`.
- **Problem:** High latency for long videos and lack of error handling for network issues or blocked content.
- **Suggestion:**
  - Use `yt-dlp`'s Python API instead of shell commands.
  - Implement video clipping: users usually only want to analyze a specific rally. Adding start/end time inputs would drastically reduce processing time.

### B. CV Pipeline Efficiency
`HybridCVPipeline` samples frames at a fixed FPS.
- **Problem:** If `TRACKING_SAMPLE_FPS` is high, processing is slow. If low, tracking might lose the player during fast movements.
- **Suggestion:**
  - Implement "Keyframe-only" pose extraction (only run MediaPipe on frames where a shot is detected).
  - Use a more robust tracker (like ByteTrack, which is available in Ultralytics) to handle occlusions.

## 4. Security & Validation

### A. Missing Authentication
`owner_id` is passed as a header but never verified.
- **Problem:** Any client can access any analysis if they know the ID.
- **Suggestion:** Integrate a basic auth provider (e.g., Clerk, Auth0, or a simple JWT-based flow).

### B. URL Validation
The backend uses `HttpUrl` but doesn't strictly verify it's a YouTube link before starting the pipeline.
- **Problem:** Passing non-YouTube URLs might cause `yt-dlp` to fail obscurely or download unwanted content.
- **Suggestion:** Add a regex validator for YouTube domains.

## 5. Potential Enhancements

- **Interactive Report:** Allow clicking on a "Shot Event" in the analytics tab to jump to that timestamp in the video (if the video is embedded).
- **Export to PDF:** Coaches often want a physical or shareable PDF version of the report.
- **Comparison:** Allow comparing two players or two different sessions for the same player.
