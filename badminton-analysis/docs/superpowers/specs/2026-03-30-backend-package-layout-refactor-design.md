# Backend Package Layout Refactor Design

## Summary

Reformat `backend/src/badminton_analysis_api` from a flat package into a set of focused
subpackages with cleaner boundaries and clearer ownership. The goal is structural clarity, not
behavior change.

The current backend puts API wiring, orchestration, provider logic, CV pipelines, media pipelines,
and all schemas in a single flat package. This makes ownership unclear and has already produced
large files such as `service.py` and `models.py`. The refactor will reorganize the same code into
packages that better match the system's responsibilities.

## Goals

- Establish clear package boundaries by concern.
- Make ownership obvious for API, analysis orchestration, coaching, pipelines, and schemas.
- Break the flat package layout that currently encourages cross-cutting imports.
- Improve maintainability without changing behavior or API contracts.
- Update all imports to the new package structure directly.

## Non-Goals

- No user-visible feature changes.
- No backend API schema changes caused by the refactor itself.
- No compatibility shim modules for old import paths.
- No major domain redesign beyond what is necessary to support the package split.

## Current Problems

- `service.py` is too large and mixes lifecycle orchestration, analytics assembly, CV integration,
  and fallback handling.
- `models.py` acts as a shared dumping ground for unrelated schemas.
- `coach_feedback.py`, `cv.py`, and `media.py` mix protocol definitions, implementations, and env
  factories at the top level of the package.
- `main.py` is doing both bootstrap and route declaration directly in the root package.

## Target Package Layout

```text
badminton_analysis_api/
  api/
    __init__.py
    app.py
  analyses/
    __init__.py
    progress.py
    service.py
    store.py
  coaching/
    __init__.py
    engine.py
  pipelines/
    __init__.py
    cv/
      __init__.py
      pipeline.py
    media/
      __init__.py
      pipeline.py
  schemas/
    __init__.py
    analysis.py
    coaching.py
    cv.py
    report.py
    shared.py
```

## Ownership Model

### `api/`

Contains FastAPI application bootstrap and route declarations only. This package should depend on
orchestration services and schema types but should not own domain logic.

### `analyses/`

Contains the analysis lifecycle as the core application domain:

- lifecycle orchestration
- progress stage definitions
- storage access
- report assembly

This is the main owner package for workflow behavior.

### `coaching/`

Contains the coach feedback boundary:

- engine protocol
- placeholder fallback implementation
- provider-backed LLM implementation
- env-based engine factory

This isolates AI/provider concerns from analysis orchestration.

### `pipelines/cv/`

Contains the CV boundary:

- CV protocol
- mock implementation
- hybrid implementation
- environment builder

This makes CV dependencies explicit and keeps them separate from business workflow code.

### `pipelines/media/`

Contains the media ingestion and setup-frame preparation boundary:

- media protocol
- mock implementation
- shell implementation
- environment builder

This isolates external command execution and artifact preparation from the rest of the app.

### `schemas/`

Splits the current all-in-one `models.py` into focused Pydantic modules:

- `shared.py` for shared primitives such as court points, boxes, and common enums
- `analysis.py` for lifecycle and setup/request-response schemas
- `coaching.py` for coach view and coaching-result schemas
- `cv.py` for tracking, pose, and setup-detection schemas
- `report.py` for analytics, evidence, and report payloads

`schemas/__init__.py` should provide a clean import surface for internal package consumers.

## Migration Strategy

1. Split schemas first.
2. Move coaching into `coaching/engine.py`.
3. Move CV and media packages into `pipelines/`.
4. Move analysis orchestration and storage into `analyses/`.
5. Move FastAPI bootstrap into `api/app.py`.
6. Update imports in tests and runtime code to the new package paths.
7. Remove the old flat modules once everything points at the new structure.

## Import Policy

- Directly update imports to the new structure.
- Do not preserve old import paths with compatibility wrappers.
- Prefer package-level imports from `schemas` where they improve readability, but keep ownership
  explicit for larger modules.

## Expected File Moves

- `main.py` -> `api/app.py`
- `service.py` -> `analyses/service.py`
- `store.py` -> `analyses/store.py`
- progress constants out of `service.py` -> `analyses/progress.py`
- `coach_feedback.py` -> `coaching/engine.py`
- `cv.py` -> `pipelines/cv/pipeline.py`
- `media.py` -> `pipelines/media/pipeline.py`
- `models.py` -> split across `schemas/*.py`

## Guardrails

- Keep runtime behavior equivalent before and after the move.
- Keep tests green after import updates.
- Avoid adding new abstractions that do not serve the package split directly.
- Only perform targeted internal cleanup when the package move requires it.

## Verification

- Backend tests pass after the refactor.
- Backend lint passes after the import churn.
- Frontend tests pass to confirm shared contract usage still works.
- Frontend build passes to confirm type changes did not break the SPA.

## Acceptance Criteria

- The backend code under `src/badminton_analysis_api` is organized into focused subpackages.
- `service.py` and `models.py` are no longer root-level flat files.
- All tests and imports are updated to the new structure.
- The app still boots and the existing test suite passes unchanged in behavior.
