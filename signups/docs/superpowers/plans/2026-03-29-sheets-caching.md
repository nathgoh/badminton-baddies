# Sheets Adapter Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 30-second TTL in-process cache to `SheetsAdapter._all_rows` to avoid hitting the Google Sheets 60 reads/min quota.

**Architecture:** Cache results of `_all_rows` per sheet name in a dict on the adapter instance. On cache miss or TTL expiry, fetch from Sheets and store. On any write (`_append`, `_update_row`), immediately invalidate that sheet's cache entry so your own writes are always visible.

**Tech Stack:** Python stdlib only (`time.monotonic`), `unittest.mock` for tests, `pytest` test runner.

---

## File Map

| File | Change |
|---|---|
| `signups/backend/storage/sheets.py` | Add `_CACHE_TTL`, `_cache` dict, `_cache_get`, `_cache_set`, `_invalidate`; modify `_all_rows`, `_append`, `_update_row` |
| `signups/backend/tests/test_sheets_cache.py` | New — unit tests for cache behaviour using mocked gspread |

---

### Task 1: Write failing cache tests

**Files:**
- Create: `signups/backend/tests/test_sheets_cache.py`

- [ ] **Step 1: Create the test file**

```python
# signups/backend/tests/test_sheets_cache.py
import time
from unittest.mock import MagicMock, patch

import pytest

from ..storage.sheets import SheetsAdapter


def make_adapter() -> SheetsAdapter:
    """Create a SheetsAdapter with all Google auth mocked out."""
    with patch("google.oauth2.service_account.Credentials.from_service_account_file"), \
         patch("gspread.authorize"):
        adapter = SheetsAdapter("fake_spreadsheet_id", "fake_creds.json")
    adapter._ss = MagicMock()
    adapter._cache = {}
    return adapter


def test_cache_hit_skips_second_sheets_call():
    """Second _all_rows call for same sheet must not hit Sheets API."""
    adapter = make_adapter()
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["id", "name"], ["abc", "foo"]]
    adapter._ss.worksheet.return_value = mock_ws

    result1 = adapter._all_rows("sessions", ["id", "name"])
    result2 = adapter._all_rows("sessions", ["id", "name"])

    assert mock_ws.get_all_values.call_count == 1
    assert result1 == result2


def test_cache_miss_after_ttl():
    """After TTL expires, _all_rows must fetch fresh data from Sheets."""
    adapter = make_adapter()
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["id"], ["1"]]
    adapter._ss.worksheet.return_value = mock_ws

    adapter._all_rows("sessions", ["id"])
    # Manually backdate the cache timestamp past the TTL
    rows, _ = adapter._cache["sessions"]
    adapter._cache["sessions"] = (rows, time.monotonic() - adapter._CACHE_TTL - 1)

    adapter._all_rows("sessions", ["id"])

    assert mock_ws.get_all_values.call_count == 2


def test_invalidate_on_append():
    """_append must invalidate the cache so next read fetches fresh data."""
    adapter = make_adapter()
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["id"], ["1"]]
    adapter._ss.worksheet.return_value = mock_ws

    adapter._all_rows("signups", ["id"])
    adapter._append("signups", ["id"], {"id": "2"})
    adapter._all_rows("signups", ["id"])

    assert mock_ws.get_all_values.call_count == 2


def test_invalidate_on_update_row():
    """_update_row must invalidate the cache so next read fetches fresh data."""
    adapter = make_adapter()
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [["id"], ["1"]]
    adapter._ss.worksheet.return_value = mock_ws

    adapter._all_rows("signups", ["id"])
    adapter._update_row("signups", ["id"], 2, {"id": "1-updated"})
    adapter._all_rows("signups", ["id"])

    assert mock_ws.get_all_values.call_count == 2


def test_different_sheets_cached_independently():
    """Cache entries for different sheet names are independent."""
    adapter = make_adapter()
    sessions_ws = MagicMock()
    sessions_ws.get_all_values.return_value = [["id"], ["s1"]]
    signups_ws = MagicMock()
    signups_ws.get_all_values.return_value = [["id"], ["sg1"]]

    def ws_side_effect(name):
        return sessions_ws if name == "sessions" else signups_ws

    adapter._ss.worksheet.side_effect = ws_side_effect

    adapter._all_rows("sessions", ["id"])
    adapter._all_rows("signups", ["id"])
    adapter._all_rows("sessions", ["id"])  # should be cache hit
    adapter._all_rows("signups", ["id"])   # should be cache hit

    assert sessions_ws.get_all_values.call_count == 1
    assert signups_ws.get_all_values.call_count == 1
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd signups
backend/.venv/bin/pytest backend/tests/test_sheets_cache.py -v
```

Expected: All 5 tests FAIL — `SheetsAdapter` has no `_cache` attribute yet, so `_cache_get`/`_cache_set`/`_invalidate` don't exist and `_all_rows` always calls Sheets.

---

### Task 2: Implement the cache

**Files:**
- Modify: `signups/backend/storage/sheets.py:1,85-105`

- [ ] **Step 1: Add `import time` at the top of the file**

The file currently starts with:
```python
import secrets
import uuid
from datetime import date, datetime, timezone
from typing import Optional
```

Change to:
```python
import secrets
import time
import uuid
from datetime import date, datetime, timezone
from typing import Optional
```

- [ ] **Step 2: Add `_CACHE_TTL`, initialise `_cache`, and add the three cache methods to `SheetsAdapter`**

Replace the existing `__init__` and the three infrastructure methods (`_ws`, `_all_rows`, `_append`, `_update_row`) with:

```python
class SheetsAdapter(StorageAdapter):
    _CACHE_TTL = 30.0

    def __init__(self, spreadsheet_id: str, credentials_file: str):
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        gc = gspread.authorize(creds)
        self._ss = gc.open_by_key(spreadsheet_id)
        self._cache: dict[str, tuple[list, float]] = {}

    def _ws(self, name: str):
        return self._ss.worksheet(name)

    def _cache_get(self, sheet_name: str) -> list | None:
        entry = self._cache.get(sheet_name)
        if entry is None:
            return None
        rows, ts = entry
        if time.monotonic() - ts > self._CACHE_TTL:
            return None
        return rows

    def _cache_set(self, sheet_name: str, rows: list) -> None:
        self._cache[sheet_name] = (rows, time.monotonic())

    def _invalidate(self, sheet_name: str) -> None:
        self._cache.pop(sheet_name, None)

    def _all_rows(self, sheet_name: str, cols: list[str]) -> list[dict[str, str]]:
        cached = self._cache_get(sheet_name)
        if cached is not None:
            return cached
        rows = self._ws(sheet_name).get_all_values()
        result = [] if len(rows) <= 1 else [_row_to_dict(cols, row) for row in rows[1:] if any(row)]
        self._cache_set(sheet_name, result)
        return result

    def _append(self, sheet_name: str, cols: list[str], data: dict) -> None:
        self._ws(sheet_name).append_row([str(data.get(col, "")) for col in cols])
        self._invalidate(sheet_name)

    def _update_row(self, sheet_name: str, cols: list[str], row_index: int, data: dict) -> None:
        values = [str(data.get(col, "")) for col in cols]
        self._ws(sheet_name).update(f"A{row_index}", [values])
        self._invalidate(sheet_name)
```

Note: `_find_row_index` is intentionally NOT changed — it calls `get_all_values()` directly because it's always called immediately before a write and must have the true current row index.

- [ ] **Step 3: Run the new cache tests**

```bash
cd signups
backend/.venv/bin/pytest backend/tests/test_sheets_cache.py -v
```

Expected output:
```
PASSED backend/tests/test_sheets_cache.py::test_cache_hit_skips_second_sheets_call
PASSED backend/tests/test_sheets_cache.py::test_cache_miss_after_ttl
PASSED backend/tests/test_sheets_cache.py::test_invalidate_on_append
PASSED backend/tests/test_sheets_cache.py::test_invalidate_on_update_row
PASSED backend/tests/test_sheets_cache.py::test_different_sheets_cached_independently
5 passed
```

- [ ] **Step 4: Run the full test suite to confirm nothing regressed**

```bash
cd signups
backend/.venv/bin/pytest backend/tests/ -v
```

Expected: All 37 tests pass (32 original + 5 new).

- [ ] **Step 5: Commit**

```bash
cd /Users/piers/code/badminton-analysis
git add signups/backend/storage/sheets.py signups/backend/tests/test_sheets_cache.py
git commit -m "feat: add 30s TTL cache to SheetsAdapter to avoid quota exhaustion"
```

---

## Self-Review

**Spec coverage:**
- ✅ Cache `_all_rows` per sheet name — Task 2 Step 2
- ✅ TTL of 30s — `_CACHE_TTL = 30.0`, tested in `test_cache_miss_after_ttl`
- ✅ Invalidate on `_append` — Task 2 Step 2 + `test_invalidate_on_append`
- ✅ Invalidate on `_update_row` — Task 2 Step 2 + `test_invalidate_on_update_row`
- ✅ `_find_row_index` bypass documented — Task 2 Step 2 note
- ✅ Existing 32 tests unaffected — confirmed in Step 4

**Placeholder scan:** None found.

**Type consistency:** `_cache: dict[str, tuple[list, float]]` — `_cache_get` returns `list | None`, `_cache_set` takes `list`, consistent throughout.
