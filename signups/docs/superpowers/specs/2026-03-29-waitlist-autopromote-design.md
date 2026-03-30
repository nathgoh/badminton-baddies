# Waitlist Auto-Promotion Design

**Date:** 2026-03-29

## Overview

When a confirmed player cancels their spot, the first person on the waitlist (by signup timestamp) is automatically promoted to confirmed status. No email notification is sent.

## Approach

Promote at cancellation time (approach A): the cancel endpoint performs the promotion synchronously in the same request, immediately after writing the cancellation.

## Backend Changes

**File:** `routers/signups.py` — cancel endpoint

Current flow:
1. Validate cancellation (window open, signup exists, not already cancelled)
2. Write `status=cancelled`, `cancelled_at=now()`

New flow:
1. Validate cancellation
2. Write `status=cancelled`, `cancelled_at=now()`
3. Recalculate confirmed count; if `confirmed_count - 1 < total_capacity`, find the earliest waitlisted signup by timestamp and promote to `confirmed`

The promotion reuses the existing `storage.update_signup(id, SignupUpdate(status=SignupStatus.confirmed))` call — no new storage methods needed.

The same logic applies to admin-initiated cancellations (admin cancel endpoint in `routers/admin.py`).

## Ordering

FIFO by `timestamp` field on the signup record — whoever joined the waitlist earliest is promoted first.

## Known Limitation

A 30-second read cache on Google Sheets means two simultaneous cancellations could both attempt to promote the same waitlisted person, resulting in one missed promotion. This is an acceptable edge case for the club's scale; the admin can manually promote via the existing endpoint.

## No Changes To

- Data models / schema
- Frontend
- API surface (no new endpoints)
- Email / notification infrastructure (none added)

## Tests

Add to `tests/test_signups.py`:
- Fill session to capacity → third signup lands on waitlist → second confirmed player cancels → waitlisted player is now confirmed
- Fill session → no waitlist → player cancels → confirmed count decreases, no error
