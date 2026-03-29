.PHONY: help install install-backend clean test lint format frontend frontend-dev frontend-build run

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install all dependencies (backend + frontend)"
	@echo "  install-backend - Install backend dependencies via uv sync"
	@echo "  clean          - Remove virtual environment"
	@echo "  test           - Run tests"
	@echo "  lint           - Run linting"
	@echo "  format         - Format code"
	@echo "  frontend       - Install frontend dependencies"
	@echo "  frontend-dev   - Start frontend dev server"
	@echo "  frontend-build - Build frontend for production"
	@echo "  run            - Run both backend and frontend (development)"

# Install backend dependencies
install-backend:
	@echo "Installing backend dependencies..."
	cd backend && uv sync --dev

# Remove virtual environment
clean:
	@echo "Removing virtual environment..."
	rm -rf backend/.venv

# Run tests
test:
	@echo "Running tests..."
	cd backend && uv run pytest tests/

# Run linting
lint:
	@echo "Running linting..."
	cd backend && uv run ruff check .

# Format code
format:
	@echo "Formatting code..."
	cd backend && uv run ruff format .

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
install: install-backend frontend
	@echo "Setup complete!"
	@echo "Backend: cd backend && uv run uvicorn main:app --reload"
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
	@cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev
