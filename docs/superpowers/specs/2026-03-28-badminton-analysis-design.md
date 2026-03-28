# Badminton Video Analysis Web App — Design Spec

## Overview

A mobile-friendly web application for analyzing badminton player performance from video. Users upload a badminton video, select a person to track, and receive AI-powered analysis including an annotated video with pose overlay and a stats dashboard.

## Tech Stack

- **Frontend:** Vite + React + TypeScript + Tailwind CSS
- **Backend:** FastAPI (Python)
- **AI/ML:** YOLOv8 nano (person detection/tracking), MediaPipe Pose (skeleton extraction)
- **Video Processing:** OpenCV

## Architecture

Monorepo with separate frontend and backend directories. Frontend dev server proxies API calls to the backend. Video files stored on backend filesystem.

```
badminton-analysis/
├── frontend/   (Vite + React + TS + Tailwind)
├── backend/    (FastAPI + YOLO + MediaPipe)
└── docs/
```

## Backend

### Structure

```
backend/
├── main.py              # FastAPI app, CORS, router includes
├── routers/
│   ├── upload.py         # POST /api/upload
│   ├── detect.py         # POST /api/detect
│   ├── analyze.py        # POST /api/analyze + status + results
│   └── video.py          # GET /api/video/{id}/{filename}
├── services/
│   ├── detection.py      # YOLO person detection logic
│   ├── tracking.py       # Track selected person across frames
│   ├── pose.py           # MediaPipe pose estimation
│   └── analysis.py       # Compute stats: distance, speed, coverage, shots
├── models/               # Pydantic schemas
├── storage/              # Uploaded + processed videos (gitignored)
└── requirements.txt
```

### Processing Pipeline

1. Load video frames with OpenCV
2. For each frame: run YOLO, match selected person via IoU with previous frame's bounding box
3. On tracked region: run MediaPipe Pose, extract landmarks
4. Accumulate: positions to distance/speed, landmarks to shot detection (wrist acceleration spikes), bounding box positions to court coverage
5. Render annotated video: draw skeleton, bounding box, movement trail
6. Save stats JSON + annotated video to storage

## Frontend

### Structure

```
frontend/
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── UploadPage.tsx
│   │   ├── SelectPage.tsx
│   │   └── ResultsPage.tsx
│   ├── components/
│   │   ├── VideoUploader.tsx
│   │   ├── PersonSelector.tsx
│   │   ├── ProcessingStatus.tsx
│   │   ├── StatsPanel.tsx
│   │   ├── StatChart.tsx
│   │   └── VideoPlayer.tsx
│   ├── api/
│   │   └── client.ts
│   └── types/
│       └── index.ts
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

### User Flow (3 screens)

1. **Upload** — Mobile-friendly upload zone with drag-and-drop or tap to pick. Shows upload progress. Navigates to Select on success.
2. **Select Person** — Displays the first frame with YOLO-detected bounding boxes as tappable overlays. User taps a person to select them.
3. **Results** — Processing spinner while analysis runs (polls status). When done: annotated video player + stats dashboard (distance, speed, court coverage, shot count, movement chart).

### Mobile-First Design

- Single-column layout, full-width components
- Large tap targets for person selection
- Bottom-anchored action buttons
- Responsive: stacks on mobile, side-by-side on wider screens for results

### Routing

React Router: `/`, `/select/:videoId`, `/results/:videoId`

## API Contract

### POST /api/upload
Upload a video file.
- Response: `{ video_id: string, filename: string }`

### POST /api/detect
Run person detection on a frame.
- Body: `{ video_id: string, frame_number?: number }`
- Response: `{ frame_image: string (base64), persons: BoundingBox[] }`
- BoundingBox: `{ id: number, x: number, y: number, width: number, height: number, confidence: number }`

### POST /api/analyze
Start analysis for a selected person.
- Body: `{ video_id: string, person_bbox: BoundingBox }`
- Response: `{ analysis_id: string, status: "processing" }`

### GET /api/analyze/{analysis_id}/status
Poll analysis progress.
- Response: `{ status: "processing" | "completed" | "failed", progress?: number }`

### GET /api/analyze/{analysis_id}/results
Fetch completed analysis.
- Response:
```json
{
  "stats": {
    "total_distance_meters": 0,
    "avg_speed_mps": 0,
    "court_coverage_pct": 0,
    "estimated_shot_count": 0,
    "movement_over_time": [{ "time_sec": 0, "distance": 0 }]
  },
  "annotated_video_url": ""
}
```

### GET /api/video/{video_id}/{filename}
Serve video files (original or annotated).

## Assumptions

- Videos are short-to-medium length (30s to 5min) — background task processing is sufficient
- Court coverage is estimated as percentage of video frame area visited (court calibration is a future enhancement)
- Shot detection is heuristic (wrist landmark acceleration threshold)
- Person tracking uses frame-to-frame IoU matching (sufficient for single-camera badminton footage)
