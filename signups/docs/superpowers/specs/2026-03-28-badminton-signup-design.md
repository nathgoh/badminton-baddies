# Badminton Court Signup Webapp — Design Spec
**Date:** 2026-03-28

## Overview

A webapp to replace the current Google Forms + Sheets signup workflow for weekly badminton sessions (HBB). Players sign up via a secret link, see who else is coming, and can cancel within a time window. Admins configure sessions, manage rosters, and calculate cost splits.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI (Python) |
| Storage | Google Sheets API |
| Auth | Google OAuth (admin only) |

The backend exposes a `StorageAdapter` interface in front of all Google Sheets calls. This makes the storage layer swappable (e.g. to Postgres) without touching business logic.

---

## Repository Structure

```
badminton-analysis/
└── signups/                   # All signup project files live here
    ├── frontend/              # Vite + React + TypeScript
    │   ├── src/
    │   │   ├── pages/         # SignupPage, RosterPage, AdminDashboard, AdminPlayers
    │   │   ├── components/
    │   │   └── api/           # Typed API client
    │   └── vite.config.ts
    ├── backend/               # FastAPI (Python)
    │   ├── main.py            # App entrypoint, serves frontend/dist as static files
    │   ├── storage/
    │   │   ├── adapter.py     # StorageAdapter interface
    │   │   └── sheets.py      # Google Sheets implementation
    │   ├── routers/
    │   │   ├── sessions.py    # Session + court CRUD
    │   │   ├── signups.py     # Signup, cancel, lookup
    │   │   └── admin.py       # Admin-only endpoints
    │   └── auth.py            # Google OAuth + admin whitelist check
    └── docs/                  # Design specs and documentation
```

FastAPI serves the built Vite output (`frontend/dist`) as static files. A single deployment unit (Render, Railway, Fly.io, etc.).

---

## Google Sheets Structure

One spreadsheet with five tabs.

### `sessions`
| Column | Type | Notes |
|---|---|---|
| id | string | e.g. `sess_001` |
| name | string | e.g. "HBB Wednesday 3/25/26" |
| date | date | The play date |
| is_active | boolean | When true, the signup form is open. When false, the public page shows "Signups are closed" and the form is hidden (roster tab still accessible). Only one session should be active at a time. |
| cancel_window_hours | integer | Hours before session date after which self-cancel is disabled (e.g. 48) |
| access_token | string | Random token used in the public URL `/s/:token` |
| created_at | datetime | |

### `courts`
| Column | Type | Notes |
|---|---|---|
| id | string | |
| session_id | string | FK → sessions.id |
| name | string | e.g. "Doubles Court" |
| start_time | time | e.g. "19:00" |
| end_time | time | e.g. "22:00" |
| max_players | integer | Capacity contributed to the session total |
| total_cost | decimal | Cost contributed to the session total |

Session total capacity = sum of all court `max_players` for that session.
Session total cost = sum of all court `total_cost` for that session.

### `signups`
| Column | Type | Notes |
|---|---|---|
| id | string | |
| session_id | string | FK → sessions.id |
| timestamp | datetime | When the signup was submitted |
| email | string | |
| name | string | Name at time of signup (snapshot, not a live FK to players) |
| status | enum | `confirmed`, `waitlist`, `cancelled` |
| payment_agreed | boolean | Player checked the payment agreement box |
| amount_owed | decimal | Set when admin calculates costs; null until then |
| amount_adjusted | boolean | True if admin has manually overridden amount_owed |
| cancelled_at | datetime | Populated when status → cancelled |

### `players`
| Column | Type | Notes |
|---|---|---|
| email | string | Primary key |
| name | string | Most recent name used |
| venmo_or_phone | string | Required; shown admin-only |
| first_seen | datetime | Timestamp of first signup |
| last_seen | datetime | Timestamp of most recent signup |

### `admins`
| Column | Type | Notes |
|---|---|---|
| email | string | Google account email |
| added_at | datetime | |

---

## Pages & Routes

### Public (requires valid session `access_token` in URL)

#### `GET /s/:token` — Signup page (default tab)
- Displays session name, date, and court cards (name, time, spots filled / total, waitlist count if full)
- Signup form fields:
  - Email (required) — on blur, looks up player record and auto-fills name + venmo_or_phone
  - Name (required)
  - Venmo or phone number (required)
  - Payment agreement checkbox (required): "I agree to pay if I do not cancel 48 hrs in advance unless I can find someone to fill in"
- Submit behaviour:
  - If email is already confirmed or waitlisted for this session → reject with "You're already signed up for this session"
  - If confirmed spots available → status = `confirmed`
  - If session is at capacity → status = `waitlist`; user is informed inline
  - On submit, player record is created or updated with submitted name + venmo_or_phone
- Cancel section (bottom of same page):
  - Email input → "Look up my signup" button
  - If found and within cancellation window: shows signup details + "Cancel my spot" button
  - If outside cancellation window: shows signup details but cancel is disabled with explanation
  - If not found: shows "No signup found for this email"

#### `GET /s/:token` (Roster tab)
- Shows confirmed players (numbered by signup order) and waitlist players (W1, W2…) by name only
- No emails, no Venmo/phone shown
- Visible to anyone with the link — no authentication required

#### `robots.txt`
```
User-agent: *
Disallow: /
```
All pages include `<meta name="robots" content="noindex, nofollow">`.

---

### Admin (Google OAuth required, email must be in `admins` sheet)

#### `GET /admin` — Session list
- Lists all sessions (name, date, active status, player count)
- "New session" button → form to create session + add courts

#### `GET /admin/sessions/:id` — Session detail
- **Left panel:** Session metadata (name, date, active toggle, edit button); court list (name, times, capacity, cost); cost split calculator
- **Cost split calculator:**
  - Shows: total court cost, confirmed player count, base cost per player
  - "Calculate & assign costs" button: sets `amount_owed = total_cost / confirmed_count` for all confirmed players where `amount_adjusted = false`
  - Players with `amount_adjusted = true` are skipped on recalculate
- **Right panel — Roster:**
  - Confirmed players table: name, email, Venmo/phone, status badge, amount owed (orange ✎ if manually adjusted), Edit + Remove buttons
  - Edit opens inline amount field; saving sets `amount_adjusted = true`
  - Waitlist section: name, email, Venmo/phone, Promote button, Remove button
  - Promote moves player to `confirmed` regardless of capacity
- **Signup link section:**
  - Displays full public URL (`yourdomain.com/s/:token`)
  - Copy button
  - Regenerate button (generates new token, old link stops working immediately)

#### `GET /admin/players` — Player database
- Table of all players: email, name, venmo_or_phone, first_seen, last_seen
- Inline edit for name and venmo_or_phone per row

---

## Key Behaviours

### Signup & waitlist
- Signup order determines waitlist position (sorted by `timestamp`)
- When a confirmed player is cancelled (by self or admin), the slot is **not** automatically filled — admin manually promotes from waitlist
- Admin can promote from waitlist even when session is at or over capacity

### Self-cancellation window
- Player can self-cancel if: `now < session.date - cancel_window_hours`
- Outside the window, only admin can cancel
- Cancellation sets `status = cancelled` and `cancelled_at = now`

### Cost calculation
- Base amount = `sum(court.total_cost) / count(confirmed signups)`
- Admin triggers calculation manually; it skips players with `amount_adjusted = true`
- Admin can edit any individual player's amount, which sets `amount_adjusted = true`

### Player record upsert
- On every signup submission, the backend upserts the `players` sheet row for that email: updates name, venmo_or_phone, last_seen. Creates the row if it doesn't exist (sets first_seen).

### Access token
- `access_token` is a cryptographically random string (e.g. 8 chars, URL-safe)
- Stored on the session row; validated on every public request
- Regenerating generates a new token and overwrites the old one — old URLs immediately return 404

---

## StorageAdapter Interface (key methods)

```python
# Sessions
get_active_session() -> Session | None
get_session_by_token(token: str) -> Session | None
list_sessions() -> list[Session]
create_session(data: SessionCreate) -> Session
update_session(id: str, data: SessionUpdate) -> Session
delete_session(id: str) -> None

# Courts
get_courts(session_id: str) -> list[Court]
create_court(data: CourtCreate) -> Court
update_court(id: str, data: CourtUpdate) -> Court
delete_court(id: str) -> None

# Signups
get_signups(session_id: str) -> list[Signup]
create_signup(data: SignupCreate) -> Signup
update_signup(id: str, data: SignupUpdate) -> Signup
cancel_signup(id: str) -> Signup

# Players
get_player(email: str) -> Player | None
upsert_player(data: PlayerUpsert) -> Player
list_players() -> list[Player]

# Admins
is_admin(email: str) -> bool
```

---

## Out of Scope (MVP)

- Email notifications of any kind
- Player authentication (players never log in)
- Payment processing or tracking (Venmo/phone is informational only)
- Multiple simultaneous active sessions
- Mobile app
