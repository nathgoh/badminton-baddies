# Sheets Adapter Caching Design

## Goal

Add a per-sheet TTL cache to `SheetsAdapter` to avoid hitting the Google Sheets 60 reads/min quota during normal use.

## Problem

Every HTTP request to the app triggers multiple `get_all_values()` calls to Google Sheets (one per sheet read). An admin session page alone hits sessions, courts, signups, and the admins tab. Under light concurrent use this quickly exhausts the quota, causing 429 errors and a stuck loading UI.

## Approach

In-process TTL cache inside `SheetsAdapter`. Cache `_all_rows` results per sheet name. Invalidate on any write. 30-second TTL as a safety net.

## Architecture

All changes are contained in `signups/backend/storage/sheets.py`.

### Cache structure

```python
_cache: dict[str, tuple[list[dict[str, str]], float]]
# sheet_name → (rows, time.monotonic() timestamp)
```

### TTL

30 seconds, hardcoded as a class constant `_CACHE_TTL = 30.0`.

### Cache methods

- `_cache_get(sheet_name) -> list | None` — returns cached rows if younger than TTL, else `None`
- `_cache_set(sheet_name, rows)` — stores rows with current timestamp
- `_invalidate(sheet_name)` — deletes the cache entry for that sheet

### Integration points

| Method | Change |
|---|---|
| `_all_rows` | Check `_cache_get` first; fetch and `_cache_set` on miss |
| `_append` | Call `_invalidate(sheet_name)` after writing |
| `_update_row` | Call `_invalidate(sheet_name)` after writing |

`_find_row_index` reads via `self._ws(...).get_all_values()` directly (not `_all_rows`), so it bypasses the cache — this is intentional, as it's always called immediately before a write and needs the true row index.

### Write visibility

Write-invalidation ensures your own writes are visible immediately on the next read. The TTL only matters if Sheets is edited externally (e.g. manual edits in the browser).

## Testing

New unit tests in `signups/backend/tests/test_sheets_cache.py` using `unittest.mock.patch` on `gspread`:

- Cache hit: second call to `_all_rows` for same sheet does not call `get_all_values` again
- Cache miss after TTL: after advancing time past 30s, `_all_rows` fetches fresh data
- Invalidation: after `_append` or `_update_row`, next `_all_rows` fetches fresh data

Existing 32 tests use `InMemoryAdapter` — unaffected.

## Out of scope

- No env var for TTL (not needed in practice)
- No cross-process cache (single-process app)
- No Redis or external cache
