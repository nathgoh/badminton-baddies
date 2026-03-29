.PHONY: help venv install dev-install clean test lint format frontend frontend-dev frontend-dev-backend run

# Default target
help:
	@echo "Available commands:"
	@echo "  venv         - Create UV virtual environment"
	@echo "  install      - Install dependencies in venv"
	@echo "  clean        - Remove virtual environment"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  frontend     - Install frontend dependencies"
	@echo "  frontend-dev - Start frontend dev server"
	@echo "  frontend-build - Build frontend for production"
	@echo "  run          - Run both backend and frontend (development)"
	@echo "  all          - Create venv and install all dependencies"

# Create UV virtual environment
venv:
	@echo "Creating UV virtual environment..."
	uv venv

# Install dependencies
install-backend: venv
	@echo "Installing dependencies..."
	uv pip install -r backend/requirements.txt

# Remove virtual environment
clean:
	@echo "Removing virtual environment..."
	rm -rf .venv

# Run tests
test:
	@echo "Running tests..."
	uv run pytest backend/tests/

# Run linting
lint:
	@echo "Running linting..."
	uv run ruff check backend/

# Format code
format:
	@echo "Formatting code..."
	uv run ruff format backend/

# Install frontend dependencies
frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Start frontend dev server
frontend-dev:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

# Build frontend for production
frontend-build:
	@echo "Building frontend..."
	cd frontend && npm run build

# Complete setup
install: venv install-backend frontend
	@echo "Setup complete!"
	@echo "Backend: uv run uvicorn backend.main:app --reload"
	@echo "Frontend: make frontend-dev"
	@echo "Or run both together: make run"

# Run both backend and frontend (development mode)
run:
	@echo "Starting backend and frontend in development mode..."
	@echo "Backend will be available at: http://localhost:8000"
	@echo "Frontend will be available at: http://localhost:5173"
	@echo "Press Ctrl+C to stop both servers"
	@echo ""
	@# Start backend in background, then frontend
	@uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev
