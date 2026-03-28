# Badminton Analysis

A mobile-friendly web app for analyzing badminton player performance from video using AI.

## What It Does

1. **Upload** a badminton video
2. **Select** the player you want to track (tap on detected persons)
3. **Get analysis** — annotated video with pose overlay + performance stats dashboard

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python) |
| Person Detection | YOLOv8 nano |
| Pose Estimation | MediaPipe Pose |
| Video Processing | OpenCV |

## Architecture

```
badminton-analysis/
├── frontend/    # React SPA (mobile-first)
├── backend/     # FastAPI + AI pipeline
└── docs/        # Design specs
```

Monorepo with separate frontend and backend. The frontend dev server proxies API calls to the backend during development.

## Analysis Pipeline

1. YOLO detects people in the video frame
2. User selects which person to track
3. Frame-by-frame tracking via IoU matching
4. MediaPipe extracts pose landmarks on the tracked person
5. Stats computed: distance traveled, average speed, court coverage, estimated shot count
6. Annotated video rendered with skeleton overlay, bounding box, and movement trail

## Analysis Output

- **Annotated video** — Original video with pose skeleton, tracking box, and movement trail overlay
- **Stats dashboard** — Total distance, average speed, court coverage %, shot count, movement over time chart

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to the backend at `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload a video file |
| POST | `/api/detect` | Detect persons in a video frame |
| POST | `/api/analyze` | Start analysis for a selected person |
| GET | `/api/analyze/{id}/status` | Poll analysis progress |
| GET | `/api/analyze/{id}/results` | Fetch analysis results |
| GET | `/api/video/{id}/{filename}` | Serve video files |
