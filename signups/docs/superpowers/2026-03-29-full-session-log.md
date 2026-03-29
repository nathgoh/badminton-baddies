# Full Session Log

Date: 2026-03-29
Worktree: `/Users/piers/code/badminton-analysis/.worktrees/backend-api`

## Scope Completed

Implemented three major areas in this session:

1. Backend API from `2026-03-29-plan-1-backend-api.md`
2. Storage/auth code from `2026-03-29-plan-2-storage-auth.md`
3. Frontend from `2026-03-29-plan-3-frontend.md`

## Backend API

Built the FastAPI backend under `signups/backend/` with:

- `main.py` app factory
- shared Pydantic models
- `StorageAdapter` abstraction
- `InMemoryAdapter`
- sessions/courts router
- public signup/cancel router
- admin router
- robots.txt endpoint
- pytest coverage for sessions, signups, admin, and auth

Additional implementation notes:

- Added `signups/backend/__init__.py` so package-relative imports work in tests and module loading.
- Added `signups/pytest.ini` to disable `pytest-asyncio` because the pinned plugin version crashed collection in this environment.
- Added `.gitignore` updates for local worktrees, backend virtualenv, and pytest cache.

## Storage and Auth

Implemented:

- `signups/backend/storage/sheets.py`
- `signups/backend/auth.py`
- `signups/backend/middleware.py`
- env-driven storage selection in `signups/backend/main.py`
- Google ID token exchange endpoint at `/auth/google`
- JWT-based admin protection

Configured local environment:

- created `signups/backend/.env`
- created `signups/backend/.env.example`
- created `signups/backend/.gitignore`
- used credentials file at `/Users/piers/Downloads/badminton-454508-90da63335eb0.json`
- set spreadsheet ID `1Xs6Wb7pCIZFtxBL7k_hSZ2UR9K0466qM9__oA17L5vo`
- set Google OAuth client ID `516551254240-ob9ft7nlcp4n9c39h09cpvv3sha5cf4n.apps.googleusercontent.com`
- generated and stored a JWT secret in `.env`

Live Google Sheets work completed:

- verified the service account could open the spreadsheet
- detected the spreadsheet only had `Sheet1`
- created/configured tabs:
  - `sessions`
  - `courts`
  - `signups`
  - `players`
  - `admins`
- wrote the required header rows
- filled `added_at` for `me@pierskwan.com` with:
  - `2026-03-29T09:28:59.877733+00:00`

Live Sheets smoke test result:

- `Sessions: []`
- `Is admin test@example.com: False`

## Backend Tightening Done During Frontend Prep

Before frontend implementation, tightened the backend so session/court management also requires admin auth.

Also updated the public session payload to include `signups` so the frontend roster tab can render from `/api/public/:token`.

## Frontend

Created the Vite React frontend under `signups/frontend/` with:

- project scaffolding (`package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`)
- frontend `.env` with the Google client ID
- typed API client
- admin auth hook
- protected route
- public signup page
- roster and cancel components
- admin login page
- admin session list/create page
- admin session detail page
- admin player database page

Production integration completed:

- frontend build outputs to `signups/backend/dist/`
- backend now serves built assets and falls back to `dist/index.html` for SPA routes like `/s/:token` and `/admin/...`

## Verification Run

Executed and confirmed:

- `backend/.venv/bin/pytest backend/tests -v`
  - final result: `32 passed`
- `npm install` in `signups/frontend`
- `npm run build` in `signups/frontend`
  - output generated in `signups/backend/dist/`
- backend SPA fallback test:
  - `GET /s/test-token` returned `200`
  - response contained `HBB Signups`

## Known Residual Items

- Browser-based manual verification of the frontend is still pending.
- Real `/auth/google` end-to-end verification still needs a browser-generated Google ID token from the frontend.
- There is an environment warning from `urllib3` about LibreSSL vs OpenSSL on this machine, but it did not block tests or live Sheets access.

## Additional Browser Testing and UI Fixes

After the initial implementation, additional work was completed in the browser-testing phase:

- started the backend locally and opened the built app at `http://127.0.0.1:8000/admin/login`
- confirmed the built frontend was being served successfully by FastAPI
- hit a Google OAuth `origin_mismatch` error when signing in from the backend-served frontend
- identified the cause: the OAuth client allowed `http://localhost:5173` but the actual app origin during testing was `http://127.0.0.1:8000`
- updated the recommended Google OAuth origins to include backend-served localhost/127.0.0.1 testing origins
- confirmed admin login worked after the origin fix

Admin session form layout fixes completed:

- added a global CSS reset in `signups/frontend/src/styles.css`
- imported that stylesheet in `signups/frontend/src/main.tsx`
- fixed the original form sizing issue by applying `box-sizing: border-box`
- identified a second root cause: the court-row layout itself still overflowed on narrower viewports
- created a design note:
  - `signups/docs/superpowers/specs/2026-03-29-admin-session-form-responsive-design.md`
- created a focused implementation plan:
  - `signups/docs/superpowers/plans/2026-03-29-plan-4-admin-session-form-responsive.md`
- implemented responsive stacked court-entry rows in:
  - `signups/frontend/src/pages/AdminSessionList.tsx`
- preserved horizontal layout on wider screens and switched to a stacked single-column layout below the breakpoint

Verification for these follow-up fixes:

- `npm run build`
  - passed after the box-sizing fix
  - passed after the responsive stacked-layout fix

## Related Files

- Previous backend-only log:
  - `signups/docs/superpowers/2026-03-29-backend-api-implementation-log.md`
