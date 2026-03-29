# Badminton Video Analysis

A web application for analyzing badminton player performance from video using AI-powered computer vision.

## Features

- **Video Upload**: Drag-and-drop interface for uploading badminton videos
- **Player Detection**: AI-powered person detection with YOLOv8
- **Player Tracking**: Frame-by-frame tracking of selected player
- **Performance Analysis**: 
  - Total distance traveled
  - Average speed
  - Court coverage percentage
  - Shot detection via motion analysis
- **Annotated Video**: Output video with bounding boxes, movement trails, and pose overlays
- **Interactive Dashboard**: Charts and statistics for performance insights

## Tech Stack

### Backend
- **FastAPI** (Python) - REST API framework
- **OpenCV** - Video processing
- **Ultralytics YOLOv8** - Person detection
- **MediaPipe** - Pose estimation (placeholder)
- **NumPy** - Numerical computations

### Frontend
- **React 18** with TypeScript
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **Recharts** - Data visualization
- **Lucide React** - Icons

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 20+
- UV package manager (recommended)

### Backend Setup

```bash
# Install dependencies and setup virtual environment
make install

# Run tests
make test

# Start backend server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Install frontend dependencies
cd frontend
npm install

# Start frontend dev server
npm run dev
```

The frontend will be available at `http://localhost:5173` and will automatically proxy API requests to the backend.

## Usage

1. **Upload Video**: Navigate to the home page and upload a badminton video (MP4, AVI, MOV)
2. **Select Player**: Click on the detected person you want to analyze
3. **View Results**: Wait for analysis to complete, then view:
   - Performance statistics
   - Movement over time chart
   - Annotated video with tracking overlays

## API Endpoints

- `POST /api/upload` - Upload video file
- `POST /api/detect` - Detect persons in video frame
- `POST /api/analyze` - Start analysis for selected person
- `GET /api/analyze/{id}/status` - Check analysis status
- `GET /api/analyze/{id}/results` - Get analysis results
- `GET /api/video/{id}/{filename}` - Serve video files

## Project Structure

```
badminton-analysis/
├── backend/                 # FastAPI backend
│   ├── main.py             # FastAPI app
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   ├── models/             # Pydantic schemas
│   └── tests/              # Backend tests
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── api/           # API client
│   │   └── types/         # TypeScript types
│   └── package.json
├── docs/                   # Documentation
└── Makefile               # Development commands
```

## Development

### Running Tests

```bash
# Backend tests
make test

# Frontend tests (if available)
cd frontend && npm test
```

### Code Quality

```bash
# Lint backend
make lint

# Format backend
make format
```

## Limitations

- **MediaPipe Pose**: Currently a placeholder implementation due to model file requirements
- **Video Length**: Limited to 300 frames for demo purposes
- **Shot Detection**: Heuristic-based, may have false positives/negatives
- **Court Calibration**: Uses frame-based coverage rather than real court dimensions

## Future Enhancements

- [ ] Implement proper MediaPipe pose estimation
- [ ] Add real court calibration
- [ ] Support for longer videos
- [ ] Multi-player analysis
- [ ] Export analysis reports
- [ ] User authentication and data persistence

## License

This project is licensed under the MIT License.
