import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

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


class InMemoryAdapter(StorageAdapter):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._courts: dict[str, Court] = {}
        self._signups: dict[str, Signup] = {}
        self._players: dict[str, Player] = {}
        self._admins: set[str] = set()

    def add_admin(self, email: str) -> None:
        self._admins.add(email)

    def get_session_by_token(self, token: str) -> Optional[Session]:
        return next((session for session in self._sessions.values() if session.access_token == token), None)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def create_session(self, data: SessionCreate) -> Session:
        session = Session(
            id=uuid.uuid4().hex[:8],
            access_token=secrets.token_urlsafe(32),
            created_at=datetime.now(timezone.utc),
            **data.model_dump(),
        )
        self._sessions[session.id] = session
        return session

    def update_session(self, id: str, data: SessionUpdate) -> Session:
        if id not in self._sessions:
            raise KeyError(id)
        updated = self._sessions[id].model_copy(update=data.model_dump(exclude_none=True))
        self._sessions[id] = updated
        return updated

    def delete_session(self, id: str) -> None:
        if id not in self._sessions:
            raise KeyError(id)
        del self._sessions[id]
        self._courts = {court_id: court for court_id, court in self._courts.items() if court.session_id != id}
        self._signups = {signup_id: signup for signup_id, signup in self._signups.items() if signup.session_id != id}

    def get_courts(self, session_id: str) -> list[Court]:
        return [court for court in self._courts.values() if court.session_id == session_id]

    def create_court(self, data: CourtCreate) -> Court:
        court = Court(id=uuid.uuid4().hex[:8], **data.model_dump())
        self._courts[court.id] = court
        return court

    def update_court(self, id: str, data: CourtUpdate) -> Court:
        if id not in self._courts:
            raise KeyError(id)
        updated = self._courts[id].model_copy(update=data.model_dump(exclude_none=True))
        self._courts[id] = updated
        return updated

    def delete_court(self, id: str) -> None:
        if id not in self._courts:
            raise KeyError(id)
        del self._courts[id]

    def get_signups(self, session_id: str) -> list[Signup]:
        return sorted(
            [signup for signup in self._signups.values() if signup.session_id == session_id],
            key=lambda signup: signup.timestamp,
        )

    def create_signup(self, data: SignupCreate) -> Signup:
        signup = Signup(
            id=uuid.uuid4().hex[:8],
            timestamp=datetime.now(timezone.utc),
            status=SignupStatus.confirmed,
            amount_adjusted=False,
            **data.model_dump(),
        )
        self._signups[signup.id] = signup
        return signup

    def update_signup(self, id: str, data: SignupUpdate) -> Signup:
        if id not in self._signups:
            raise KeyError(id)
        updated = self._signups[id].model_copy(update=data.model_dump(exclude_none=True))
        self._signups[id] = updated
        return updated

    def get_player(self, email: str) -> Optional[Player]:
        return self._players.get(email)

    def upsert_player(self, data: PlayerUpsert) -> Player:
        existing = self._players.get(data.email)
        if existing:
            player = existing.model_copy(
                update={
                    "name": data.name,
                    "venmo_or_phone": data.venmo_or_phone,
                    "last_seen": datetime.now(timezone.utc),
                }
            )
        else:
            now = datetime.now(timezone.utc)
            player = Player(first_seen=now, last_seen=now, **data.model_dump())
        self._players[data.email] = player
        return player

    def list_players(self) -> list[Player]:
        return list(self._players.values())

    def is_admin(self, email: str) -> bool:
        return email in self._admins

