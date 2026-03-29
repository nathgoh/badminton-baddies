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


def make_worksheet(adapter: SheetsAdapter, data: list) -> MagicMock:
    """Create a mock worksheet returning the given rows and attach it to the adapter."""
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = data
    adapter._ss.worksheet.return_value = mock_ws
    return mock_ws


def test_cache_hit_skips_second_sheets_call():
    """Second _all_rows call for same sheet must not hit Sheets API."""
    adapter = make_adapter()
    mock_ws = make_worksheet(adapter, [["id", "name"], ["abc", "foo"]])

    result1 = adapter._all_rows("sessions", ["id", "name"])
    result2 = adapter._all_rows("sessions", ["id", "name"])

    assert mock_ws.get_all_values.call_count == 1
    assert result1 == result2


def test_cache_miss_after_ttl():
    """After TTL expires, _all_rows must fetch fresh data from Sheets."""
    adapter = make_adapter()
    mock_ws = make_worksheet(adapter, [["id"], ["1"]])

    adapter._all_rows("sessions", ["id"])
    # Manually backdate the cache timestamp past the TTL
    rows, _ = adapter._cache["sessions"]
    adapter._cache["sessions"] = (rows, time.monotonic() - adapter._CACHE_TTL - 1)

    adapter._all_rows("sessions", ["id"])

    assert mock_ws.get_all_values.call_count == 2


def test_invalidate_on_append():
    """_append must invalidate the cache so next read fetches fresh data."""
    adapter = make_adapter()
    mock_ws = make_worksheet(adapter, [["id"], ["1"]])

    adapter._all_rows("signups", ["id"])
    adapter._append("signups", ["id"], {"id": "2"})
    adapter._all_rows("signups", ["id"])

    assert mock_ws.get_all_values.call_count == 2


def test_invalidate_on_update_row():
    """_update_row must invalidate the cache so next read fetches fresh data."""
    adapter = make_adapter()
    mock_ws = make_worksheet(adapter, [["id"], ["1"]])

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
