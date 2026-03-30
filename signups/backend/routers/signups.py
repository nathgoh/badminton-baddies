from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

try:
    from ..dependencies import get_storage
    from ..models import (
        CancelLookupResponse,
        PlayerLookupResponse,
        PlayerUpsert,
        PublicSessionResponse,
        Signup,
        SignupCreate,
        SignupRequest,
        SignupStatus,
        SignupUpdate,
    )
    from ..storage.adapter import StorageAdapter
except ImportError:
    from dependencies import get_storage
    from models import (
        CancelLookupResponse,
        PlayerLookupResponse,
        PlayerUpsert,
        PublicSessionResponse,
        Signup,
        SignupCreate,
        SignupRequest,
        SignupStatus,
        SignupUpdate,
    )
    from storage.adapter import StorageAdapter


router = APIRouter()


class CancelRequest(BaseModel):
    signup_id: str
    email: str


def _get_session_or_404(token: str, storage: StorageAdapter):
    session = storage.get_session_by_token(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def _cancellation_cutoff(session_datetime_date, cancel_window_hours: int) -> datetime:
    session_start = datetime.combine(session_datetime_date, time.min, tzinfo=timezone.utc)
    return session_start - timedelta(hours=cancel_window_hours)


def _promote_next_from_waitlist(session_id: str, storage: StorageAdapter) -> None:
    courts = storage.get_courts(session_id)
    total_capacity = sum(court.max_players for court in courts)
    signups = storage.get_signups(session_id)
    confirmed_count = sum(1 for s in signups if s.status == SignupStatus.confirmed)
    if confirmed_count < total_capacity:
        waitlisted = sorted(
            [s for s in signups if s.status == SignupStatus.waitlist],
            key=lambda s: s.timestamp,
        )
        if waitlisted:
            storage.update_signup(waitlisted[0].id, SignupUpdate(status=SignupStatus.confirmed))


@router.get("/public/{token}", response_model=PublicSessionResponse)
def get_public_session(token: str, storage: StorageAdapter = Depends(get_storage)) -> PublicSessionResponse:
    session = _get_session_or_404(token, storage)
    courts = storage.get_courts(session.id)
    signups = storage.get_signups(session.id)
    confirmed = [signup for signup in signups if signup.status == SignupStatus.confirmed]
    waitlist = [signup for signup in signups if signup.status == SignupStatus.waitlist]
    return PublicSessionResponse(
        session=session,
        courts=courts,
        signups=[signup for signup in signups if signup.status != SignupStatus.cancelled],
        confirmed_count=len(confirmed),
        waitlist_count=len(waitlist),
        total_capacity=sum(court.max_players for court in courts),
    )


@router.post("/public/{token}/signup", response_model=Signup, status_code=status.HTTP_201_CREATED)
def create_signup(
    token: str,
    body: SignupRequest,
    storage: StorageAdapter = Depends(get_storage),
) -> Signup:
    session = _get_session_or_404(token, storage)
    if not session.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signups are closed for this session")

    signups = storage.get_signups(session.id)
    duplicate = any(
        signup.email == body.email and signup.status in {SignupStatus.confirmed, SignupStatus.waitlist}
        for signup in signups
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Signup already exists")

    courts = storage.get_courts(session.id)
    confirmed_count = sum(1 for signup in signups if signup.status == SignupStatus.confirmed)
    total_capacity = sum(court.max_players for court in courts)

    signup = storage.create_signup(
        SignupCreate(
            session_id=session.id,
            email=body.email,
            name=body.name,
            payment_agreed=body.payment_agreed,
        )
    )

    if confirmed_count >= total_capacity:
        signup = storage.update_signup(signup.id, SignupUpdate(status=SignupStatus.waitlist))

    storage.upsert_player(
        PlayerUpsert(email=body.email, name=body.name, venmo_or_phone=body.venmo_or_phone)
    )
    return signup


@router.get("/public/{token}/player-lookup", response_model=PlayerLookupResponse)
def player_lookup(
    token: str, email: str, storage: StorageAdapter = Depends(get_storage)
) -> PlayerLookupResponse:
    _get_session_or_404(token, storage)
    player = storage.get_player(email)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return PlayerLookupResponse(name=player.name, venmo_or_phone=player.venmo_or_phone)


@router.get("/public/{token}/cancel-lookup", response_model=CancelLookupResponse)
def cancel_lookup(
    token: str, email: str, storage: StorageAdapter = Depends(get_storage)
) -> CancelLookupResponse:
    session = _get_session_or_404(token, storage)
    signup = next(
        (
            item
            for item in storage.get_signups(session.id)
            if item.email == email and item.status != SignupStatus.cancelled
        ),
        None,
    )
    if signup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No signup found for this email")

    can_cancel = datetime.now(timezone.utc) < _cancellation_cutoff(
        session.date, session.cancel_window_hours
    )
    reason = None
    if not can_cancel:
        reason = f"Cancellation closed {session.cancel_window_hours} hours before the session"
    return CancelLookupResponse(signup=signup, can_cancel=can_cancel, reason=reason)


@router.post("/public/{token}/cancel", response_model=Signup)
def cancel_signup(
    token: str, body: CancelRequest, storage: StorageAdapter = Depends(get_storage)
) -> Signup:
    session = _get_session_or_404(token, storage)
    signup = next((item for item in storage.get_signups(session.id) if item.id == body.signup_id), None)
    if signup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found")
    if signup.email != body.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email does not match this signup")
    if signup.status == SignupStatus.cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup is already cancelled")
    if datetime.now(timezone.utc) >= _cancellation_cutoff(session.date, session.cancel_window_hours):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has closed")

    cancelled = storage.update_signup(
        signup.id,
        SignupUpdate(status=SignupStatus.cancelled, cancelled_at=datetime.now(timezone.utc)),
    )
    _promote_next_from_waitlist(session.id, storage)
    return cancelled
