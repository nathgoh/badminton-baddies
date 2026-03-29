import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

try:
    from ..dependencies import get_storage
    from ..models import (
        CostCalculationResult,
        Court,
        Player,
        PlayerUpsert,
        Session,
        SessionUpdate,
        Signup,
        SignupStatus,
        SignupUpdate,
    )
    from ..storage.adapter import StorageAdapter
except ImportError:
    from dependencies import get_storage
    from models import (
        CostCalculationResult,
        Court,
        Player,
        PlayerUpsert,
        Session,
        SessionUpdate,
        Signup,
        SignupStatus,
        SignupUpdate,
    )
    from storage.adapter import StorageAdapter


router = APIRouter(prefix="/admin")


class AdminSessionResponse(BaseModel):
    session: Session
    courts: list[Court]
    signups: list[Signup]
    total_cost: float
    total_capacity: int
    confirmed_count: int
    waitlist_count: int


class SignupAmountUpdate(BaseModel):
    amount_owed: float
    amount_adjusted: bool = True


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    venmo_or_phone: Optional[str] = None


def _get_session_by_id(storage: StorageAdapter, session_id: str) -> Session:
    session = next((item for item in storage.list_sessions() if item.id == session_id), None)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/sessions/{session_id}", response_model=AdminSessionResponse)
def get_admin_session(
    session_id: str, storage: StorageAdapter = Depends(get_storage)
) -> AdminSessionResponse:
    session = _get_session_by_id(storage, session_id)
    courts = storage.get_courts(session_id)
    signups = [signup for signup in storage.get_signups(session_id) if signup.status != SignupStatus.cancelled]
    confirmed = [signup for signup in signups if signup.status == SignupStatus.confirmed]
    waitlist = [signup for signup in signups if signup.status == SignupStatus.waitlist]
    return AdminSessionResponse(
        session=session,
        courts=courts,
        signups=signups,
        total_cost=sum(court.total_cost for court in courts),
        total_capacity=sum(court.max_players for court in courts),
        confirmed_count=len(confirmed),
        waitlist_count=len(waitlist),
    )


@router.post("/sessions/{session_id}/calculate-costs", response_model=CostCalculationResult)
def calculate_costs(
    session_id: str, storage: StorageAdapter = Depends(get_storage)
) -> CostCalculationResult:
    courts = storage.get_courts(session_id)
    confirmed = [
        signup for signup in storage.get_signups(session_id) if signup.status == SignupStatus.confirmed
    ]
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed players to calculate costs for",
        )
    total_cost = sum(court.total_cost for court in courts)
    base_amount = round(total_cost / len(confirmed), 2)
    for signup in confirmed:
        if not signup.amount_adjusted:
            storage.update_signup(signup.id, SignupUpdate(amount_owed=base_amount))
    return CostCalculationResult(
        total_cost=total_cost,
        confirmed_count=len(confirmed),
        base_amount=base_amount,
    )


@router.patch("/signups/{signup_id}", response_model=Signup)
def update_signup_amount(
    signup_id: str,
    body: SignupAmountUpdate,
    storage: StorageAdapter = Depends(get_storage),
) -> Signup:
    try:
        return storage.update_signup(
            signup_id,
            SignupUpdate(amount_owed=body.amount_owed, amount_adjusted=body.amount_adjusted),
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


@router.post("/signups/{signup_id}/promote", response_model=Signup)
def promote_from_waitlist(signup_id: str, storage: StorageAdapter = Depends(get_storage)) -> Signup:
    try:
        return storage.update_signup(signup_id, SignupUpdate(status=SignupStatus.confirmed))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


@router.delete("/signups/{signup_id}", response_model=Signup)
def cancel_signup(signup_id: str, storage: StorageAdapter = Depends(get_storage)) -> Signup:
    try:
        return storage.update_signup(
            signup_id,
            SignupUpdate(status=SignupStatus.cancelled, cancelled_at=datetime.now(timezone.utc)),
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


@router.post("/sessions/{session_id}/regenerate-token", response_model=Session)
def regenerate_token(session_id: str, storage: StorageAdapter = Depends(get_storage)) -> Session:
    try:
        return storage.update_session(
            session_id, SessionUpdate(access_token=secrets.token_urlsafe(8))
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc


@router.get("/players", response_model=list[Player])
def list_players(storage: StorageAdapter = Depends(get_storage)) -> list[Player]:
    return storage.list_players()


@router.patch("/players/{email}", response_model=Player)
def update_player(
    email: str, body: PlayerUpdate, storage: StorageAdapter = Depends(get_storage)
) -> Player:
    player = storage.get_player(email)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return storage.upsert_player(
        PlayerUpsert(
            email=email,
            name=body.name or player.name,
            venmo_or_phone=body.venmo_or_phone or player.venmo_or_phone,
        )
    )

