import secrets
import time
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

try:
    from ..models import (
        Court,
        CourtCreate,
        CourtUpdate,
        Player,
        PlayerUpsert,
        Session,
        SessionCreate,
        SessionUpdate,
        Signup,
        SignupCreate,
        SignupStatus,
        SignupUpdate,
    )
    from .adapter import StorageAdapter
except ImportError:
    from models import (
        Court,
        CourtCreate,
        CourtUpdate,
        Player,
        PlayerUpsert,
        Session,
        SessionCreate,
        SessionUpdate,
        Signup,
        SignupCreate,
        SignupStatus,
        SignupUpdate,
    )
    from storage.adapter import StorageAdapter


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
SESSION_COLS = ["id", "name", "date", "is_active", "cancel_window_hours", "access_token", "created_at"]
COURT_COLS = ["id", "session_id", "name", "start_time", "end_time", "max_players", "total_cost"]
SIGNUP_COLS = [
    "id",
    "session_id",
    "timestamp",
    "email",
    "name",
    "status",
    "payment_agreed",
    "amount_owed",
    "amount_adjusted",
    "cancelled_at",
    "paid",
]
PLAYER_COLS = ["email", "name", "venmo_or_phone", "first_seen", "last_seen"]
ADMIN_COLS = ["email", "added_at"]


def _row_to_dict(headers: list[str], row: list[str]) -> dict[str, str]:
    padded = row + [""] * (len(headers) - len(row))
    return dict(zip(headers, padded))


def _parse_bool(value) -> bool:
    return str(value).upper() in {"TRUE", "1", "YES"}


def _parse_optional_float(value) -> Optional[float]:
    return float(value) if value not in ("", None) else None


def _parse_optional_datetime(value) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(str(value))


class SheetsAdapter(StorageAdapter):
    _CACHE_TTL = 30.0

    def __init__(self, spreadsheet_id: str, credentials_file: str):
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        gc = gspread.authorize(creds)
        self._ss = gc.open_by_key(spreadsheet_id)
        self._cache: dict = {}

    def _ws(self, name: str):
        return self._ss.worksheet(name)

    def _cache_get(self, sheet_name: str) -> Optional[list]:
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

    def _find_row_index(self, sheet_name: str, id_val: str) -> int:
        rows = self._ws(sheet_name).get_all_values()
        for index, row in enumerate(rows[1:], start=2):
            if row and row[0] == id_val:
                return index
        raise KeyError(id_val)

    def _row_to_session(self, row: dict[str, str]) -> Session:
        return Session(
            id=row["id"],
            name=row["name"],
            date=date.fromisoformat(row["date"]),
            is_active=_parse_bool(row["is_active"]),
            cancel_window_hours=int(row["cancel_window_hours"] or 48),
            access_token=row["access_token"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_session_by_token(self, token: str) -> Optional[Session]:
        row = next((item for item in self._all_rows("sessions", SESSION_COLS) if item["access_token"] == token), None)
        return self._row_to_session(row) if row else None

    def list_sessions(self) -> list[Session]:
        return [self._row_to_session(row) for row in self._all_rows("sessions", SESSION_COLS)]

    def create_session(self, data: SessionCreate) -> Session:
        session = Session(
            id=uuid.uuid4().hex[:8],
            access_token=secrets.token_urlsafe(8),
            created_at=datetime.now(timezone.utc),
            **data.model_dump(),
        )
        self._append(
            "sessions",
            SESSION_COLS,
            {
                "id": session.id,
                "name": session.name,
                "date": session.date.isoformat(),
                "is_active": session.is_active,
                "cancel_window_hours": session.cancel_window_hours,
                "access_token": session.access_token,
                "created_at": session.created_at.isoformat(),
            },
        )
        return session

    def update_session(self, id: str, data: SessionUpdate) -> Session:
        sessions = {session.id: session for session in self.list_sessions()}
        if id not in sessions:
            raise KeyError(id)
        updated = sessions[id].model_copy(update=data.model_dump(exclude_none=True))
        self._update_row(
            "sessions",
            SESSION_COLS,
            self._find_row_index("sessions", id),
            {
                "id": updated.id,
                "name": updated.name,
                "date": updated.date.isoformat(),
                "is_active": updated.is_active,
                "cancel_window_hours": updated.cancel_window_hours,
                "access_token": updated.access_token,
                "created_at": updated.created_at.isoformat(),
            },
        )
        return updated

    def delete_session(self, id: str) -> None:
        self._ws("sessions").delete_rows(self._find_row_index("sessions", id))
        self._invalidate("sessions")

    def _row_to_court(self, row: dict[str, str]) -> Court:
        return Court(
            id=row["id"],
            session_id=row["session_id"],
            name=row["name"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            max_players=int(row["max_players"]),
            total_cost=float(row["total_cost"]),
        )

    def get_courts(self, session_id: str) -> list[Court]:
        return [
            self._row_to_court(row)
            for row in self._all_rows("courts", COURT_COLS)
            if row["session_id"] == session_id
        ]

    def create_court(self, data: CourtCreate) -> Court:
        court = Court(id=uuid.uuid4().hex[:8], **data.model_dump())
        self._append(
            "courts",
            COURT_COLS,
            {
                "id": court.id,
                "session_id": court.session_id,
                "name": court.name,
                "start_time": court.start_time,
                "end_time": court.end_time,
                "max_players": court.max_players,
                "total_cost": court.total_cost,
            },
        )
        return court

    def update_court(self, id: str, data: CourtUpdate) -> Court:
        rows = self._all_rows("courts", COURT_COLS)
        row = next((item for item in rows if item["id"] == id), None)
        if row is None:
            raise KeyError(id)
        updated = self._row_to_court(row).model_copy(update=data.model_dump(exclude_none=True))
        self._update_row(
            "courts",
            COURT_COLS,
            self._find_row_index("courts", id),
            {
                "id": updated.id,
                "session_id": updated.session_id,
                "name": updated.name,
                "start_time": updated.start_time,
                "end_time": updated.end_time,
                "max_players": updated.max_players,
                "total_cost": updated.total_cost,
            },
        )
        return updated

    def delete_court(self, id: str) -> None:
        self._ws("courts").delete_rows(self._find_row_index("courts", id))
        self._invalidate("courts")

    def _row_to_signup(self, row: dict[str, str]) -> Signup:
        return Signup(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            email=row["email"],
            name=row["name"],
            status=SignupStatus(row["status"]),
            payment_agreed=_parse_bool(row["payment_agreed"]),
            amount_owed=_parse_optional_float(row["amount_owed"]),
            amount_adjusted=_parse_bool(row["amount_adjusted"]),
            cancelled_at=_parse_optional_datetime(row["cancelled_at"]),
            paid=_parse_bool(row.get("paid", "")),
        )

    def get_signups(self, session_id: str) -> list[Signup]:
        signups = [
            self._row_to_signup(row)
            for row in self._all_rows("signups", SIGNUP_COLS)
            if row["session_id"] == session_id
        ]
        return sorted(signups, key=lambda signup: signup.timestamp)

    def create_signup(self, data: SignupCreate) -> Signup:
        signup = Signup(
            id=uuid.uuid4().hex[:8],
            timestamp=datetime.now(timezone.utc),
            status=SignupStatus.confirmed,
            amount_adjusted=False,
            **data.model_dump(),
        )
        self._append(
            "signups",
            SIGNUP_COLS,
            {
                "id": signup.id,
                "session_id": signup.session_id,
                "timestamp": signup.timestamp.isoformat(),
                "email": signup.email,
                "name": signup.name,
                "status": signup.status.value,
                "payment_agreed": signup.payment_agreed,
                "amount_owed": signup.amount_owed or "",
                "amount_adjusted": signup.amount_adjusted,
                "cancelled_at": "",
                "paid": signup.paid,
            },
        )
        return signup

    def update_signup(self, id: str, data: SignupUpdate) -> Signup:
        rows = self._all_rows("signups", SIGNUP_COLS)
        row = next((item for item in rows if item["id"] == id), None)
        if row is None:
            raise KeyError(id)
        updated = self._row_to_signup(row).model_copy(update=data.model_dump(exclude_none=True))
        self._update_row(
            "signups",
            SIGNUP_COLS,
            self._find_row_index("signups", id),
            {
                "id": updated.id,
                "session_id": updated.session_id,
                "timestamp": updated.timestamp.isoformat(),
                "email": updated.email,
                "name": updated.name,
                "status": updated.status.value,
                "payment_agreed": updated.payment_agreed,
                "amount_owed": updated.amount_owed if updated.amount_owed is not None else "",
                "amount_adjusted": updated.amount_adjusted,
                "cancelled_at": updated.cancelled_at.isoformat() if updated.cancelled_at else "",
                "paid": updated.paid,
            },
        )
        return updated

    def _row_to_player(self, row: dict[str, str]) -> Player:
        return Player(
            email=row["email"],
            name=row["name"],
            venmo_or_phone=row["venmo_or_phone"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
        )

    def get_player(self, email: str) -> Optional[Player]:
        row = next((item for item in self._all_rows("players", PLAYER_COLS) if item["email"] == email), None)
        return self._row_to_player(row) if row else None

    def upsert_player(self, data: PlayerUpsert) -> Player:
        rows = self._all_rows("players", PLAYER_COLS)
        row = next((item for item in rows if item["email"] == data.email), None)
        if row is None:
            now = datetime.now(timezone.utc)
            player = Player(email=data.email, name=data.name, venmo_or_phone=data.venmo_or_phone, first_seen=now, last_seen=now)
            self._append(
                "players",
                PLAYER_COLS,
                {
                    "email": player.email,
                    "name": player.name,
                    "venmo_or_phone": player.venmo_or_phone,
                    "first_seen": player.first_seen.isoformat(),
                    "last_seen": player.last_seen.isoformat(),
                },
            )
            return player
        existing = self._row_to_player(row)
        updated = existing.model_copy(
            update={
                "name": data.name,
                "venmo_or_phone": data.venmo_or_phone,
                "last_seen": datetime.now(timezone.utc),
            }
        )
        self._update_row(
            "players",
            PLAYER_COLS,
            self._find_row_index("players", data.email),
            {
                "email": updated.email,
                "name": updated.name,
                "venmo_or_phone": updated.venmo_or_phone,
                "first_seen": updated.first_seen.isoformat(),
                "last_seen": updated.last_seen.isoformat(),
            },
        )
        return updated

    def list_players(self) -> list[Player]:
        return [self._row_to_player(row) for row in self._all_rows("players", PLAYER_COLS)]

    def is_admin(self, email: str) -> bool:
        return any(
            row["email"].lower() == email.lower()
            for row in self._all_rows("admins", ADMIN_COLS)
        )

