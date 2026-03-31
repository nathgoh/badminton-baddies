.PHONY: install install-backend install-frontend run run-mock check-env kill test test-backend test-frontend

check-env:
	@if test "$(VIRTUAL_ENV)" = "" ; then \
		echo "Make sure you are in a virtualenv. Run \`source backend/.venv/bin/activate\`."; \
		exit 1; \
	fi

install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && pnpm install

kill:
	@echo "Stopping services..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@echo "Stopped ports 8000 and 5173"

test: test-backend test-frontend

test-backend: check-env
	cd backend && uv run pytest

test-frontend:
	cd frontend && pnpm test

run: check-env
	@trap 'echo "Stopping services..."; lsof -ti:8000 | xargs kill -9 2>/dev/null || true; lsof -ti:5173 | xargs kill -9 2>/dev/null || true; echo "Stopped ports 8000 and 5173"' INT TERM; \
	(cd backend && MEDIA_PIPELINE=shell CV_PIPELINE=hybrid uv run uvicorn api.app:app --reload --port 8000) & \
	(cd frontend && pnpm dev) & \
	wait || true

run-mock: check-env
	@trap 'echo "Stopping services..."; lsof -ti:8000 | xargs kill -9 2>/dev/null || true; lsof -ti:5173 | xargs kill -9 2>/dev/null || true; echo "Stopped ports 8000 and 5173"' INT TERM; \
	(cd backend && uv run uvicorn api.app:app --reload --port 8000) & \
	(cd frontend && pnpm dev) & \
	wait || true
