from abc import ABC, abstractmethod
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
        SignupUpdate,
    )
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
        SignupUpdate,
    )


class StorageAdapter(ABC):
    @abstractmethod
    def get_session_by_token(self, token: str) -> Optional[Session]:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self) -> list[Session]:
        raise NotImplementedError

    @abstractmethod
    def create_session(self, data: SessionCreate) -> Session:
        raise NotImplementedError

    @abstractmethod
    def update_session(self, id: str, data: SessionUpdate) -> Session:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_courts(self, session_id: str) -> list[Court]:
        raise NotImplementedError

    @abstractmethod
    def create_court(self, data: CourtCreate) -> Court:
        raise NotImplementedError

    @abstractmethod
    def update_court(self, id: str, data: CourtUpdate) -> Court:
        raise NotImplementedError

    @abstractmethod
    def delete_court(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_signups(self, session_id: str) -> list[Signup]:
        raise NotImplementedError

    @abstractmethod
    def create_signup(self, data: SignupCreate) -> Signup:
        raise NotImplementedError

    @abstractmethod
    def update_signup(self, id: str, data: SignupUpdate) -> Signup:
        raise NotImplementedError

    @abstractmethod
    def get_player(self, email: str) -> Optional[Player]:
        raise NotImplementedError

    @abstractmethod
    def upsert_player(self, data: PlayerUpsert) -> Player:
        raise NotImplementedError

    @abstractmethod
    def list_players(self) -> list[Player]:
        raise NotImplementedError

    @abstractmethod
    def is_admin(self, email: str) -> bool:
        raise NotImplementedError

