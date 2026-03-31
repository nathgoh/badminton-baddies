from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignupStatus(str, Enum):
    confirmed = "confirmed"
    waitlist = "waitlist"
    cancelled = "cancelled"


class Session(BaseModel):
    id: str
    name: str
    date: date
    is_active: bool
    cancel_window_hours: int
    access_token: str
    created_at: datetime


class SessionCreate(BaseModel):
    name: str
    date: date
    is_active: bool = False
    cancel_window_hours: int = 48


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    is_active: Optional[bool] = None
    cancel_window_hours: Optional[int] = None
    access_token: Optional[str] = None


class Court(BaseModel):
    id: str
    session_id: str
    name: str
    start_time: str
    end_time: str
    max_players: int
    total_cost: float


class CourtCreate(BaseModel):
    session_id: str = ""
    name: str
    start_time: str
    end_time: str
    max_players: int
    total_cost: float = Field(ge=0)


class CourtUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    max_players: Optional[int] = None
    total_cost: Optional[float] = Field(default=None, ge=0)


class Signup(BaseModel):
    id: str
    session_id: str
    timestamp: datetime
    email: str
    name: str
    status: SignupStatus
    payment_agreed: bool
    amount_owed: Optional[float] = None
    amount_adjusted: bool = False
    cancelled_at: Optional[datetime] = None
    paid: bool = False


class SignupCreate(BaseModel):
    session_id: str
    email: str
    name: str
    payment_agreed: bool


class SignupUpdate(BaseModel):
    status: Optional[SignupStatus] = None
    amount_owed: Optional[float] = Field(default=None, ge=0)
    amount_adjusted: Optional[bool] = None
    cancelled_at: Optional[datetime] = None
    paid: Optional[bool] = None


class Player(BaseModel):
    email: str
    name: str
    venmo_or_phone: str
    first_seen: datetime
    last_seen: datetime


class PlayerUpsert(BaseModel):
    email: str
    name: str
    venmo_or_phone: str


class SignupRequest(BaseModel):
    email: str
    name: str
    venmo_or_phone: str
    payment_agreed: bool


class PublicSessionResponse(BaseModel):
    session: Session
    courts: list[Court]
    signups: list[Signup] = []
    confirmed_count: int
    waitlist_count: int
    total_capacity: int


class PlayerLookupResponse(BaseModel):
    name: str
    venmo_or_phone: str


class CancelLookupResponse(BaseModel):
    signup: Signup
    can_cancel: bool
    reason: Optional[str] = None


class CostCalculationResult(BaseModel):
    total_cost: float
    confirmed_count: int
    base_amount: float
