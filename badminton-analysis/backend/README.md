# Backend

FastAPI service for the badminton analysis MVP.

## Commands

```bash
uv sync --group dev
uv run uvicorn src.badminton_analysis_api.main:app --reload --port 8000
uv run pytest
uv run ruff check .
uv run ty check src
```
