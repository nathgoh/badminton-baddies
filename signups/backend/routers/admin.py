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


def _get_signup_by_id(storage: StorageAdapter, signup_id: str) -> Signup:
    for session in storage.list_sessions():
        signup = next((item for item in storage.get_signups(session.id) if item.id == signup_id), None)
        if signup is not None:
            return signup
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found")


def _validate_projected_confirmed_costs(
    session_id: str, storage: StorageAdapter, confirmed: list[Signup]
) -> tuple[float, float, list[Signup], int]:
    courts = storage.get_courts(session_id)
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed players to calculate costs for",
        )

    total_cost = sum(court.total_cost for court in courts)
    adjusted = [s for s in confirmed if s.amount_adjusted and s.amount_owed is not None]
    unadjusted = [s for s in confirmed if not s.amount_adjusted]
    adjusted_total = round(sum(s.amount_owed for s in adjusted), 2)

    if adjusted_total > round(total_cost, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjusted amounts (${adjusted_total:.2f}) exceed total cost (${total_cost:.2f})",
        )

    return total_cost, adjusted_total, unadjusted, len(confirmed)


def _recalculate_session_costs(
    session_id: str, storage: StorageAdapter
) -> CostCalculationResult:
    confirmed = [
        signup for signup in storage.get_signups(session_id) if signup.status == SignupStatus.confirmed
    ]
    total_cost, adjusted_total, unadjusted, confirmed_count = _validate_projected_confirmed_costs(
        session_id, storage, confirmed
    )

    if not unadjusted:
        return CostCalculationResult(
            total_cost=total_cost,
            confirmed_count=confirmed_count,
            base_amount=0.0,
        )

    remaining = total_cost - adjusted_total
    remaining_cents = int(round(remaining * 100))
    base_cents, extra_cents = divmod(remaining_cents, len(unadjusted))
    base_amount = round(remaining / len(unadjusted), 2)
    for index, signup in enumerate(unadjusted):
        amount_cents = base_cents + (1 if index < extra_cents else 0)
        storage.update_signup(signup.id, SignupUpdate(amount_owed=amount_cents / 100))

    return CostCalculationResult(
        total_cost=total_cost,
        confirmed_count=confirmed_count,
        base_amount=base_amount,
    )


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
    return _recalculate_session_costs(session_id, storage)


@router.patch("/signups/{signup_id}", response_model=Signup)
def update_signup_amount(
    signup_id: str,
    body: SignupAmountUpdate,
    storage: StorageAdapter = Depends(get_storage),
) -> Signup:
    try:
        existing = _get_signup_by_id(storage, signup_id)
        if existing.status == SignupStatus.confirmed:
            projected_confirmed = [
                signup.model_copy(
                    update={"amount_owed": body.amount_owed, "amount_adjusted": body.amount_adjusted}
                )
                if signup.id == signup_id
                else signup
                for signup in storage.get_signups(existing.session_id)
                if signup.status == SignupStatus.confirmed
            ]
            _validate_projected_confirmed_costs(existing.session_id, storage, projected_confirmed)

        updated = storage.update_signup(
            signup_id,
            SignupUpdate(amount_owed=body.amount_owed, amount_adjusted=body.amount_adjusted),
        )
        if updated.status == SignupStatus.confirmed:
            _recalculate_session_costs(updated.session_id, storage)
        return next(item for item in storage.get_signups(updated.session_id) if item.id == signup_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


class MarkPaidRequest(BaseModel):
    paid: bool


@router.post("/signups/{signup_id}/mark-paid", response_model=Signup)
def mark_paid(
    signup_id: str, body: MarkPaidRequest, storage: StorageAdapter = Depends(get_storage)
) -> Signup:
    try:
        return storage.update_signup(signup_id, SignupUpdate(paid=body.paid))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


@router.post("/signups/{signup_id}/promote", response_model=Signup)
def promote_from_waitlist(signup_id: str, storage: StorageAdapter = Depends(get_storage)) -> Signup:
    try:
        signup = _get_signup_by_id(storage, signup_id)
        if signup.status != SignupStatus.waitlist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only waitlisted signups can be promoted",
            )

        projected_confirmed = [
            item for item in storage.get_signups(signup.session_id)
            if item.status == SignupStatus.confirmed
        ]
        projected_confirmed.append(signup.model_copy(update={"status": SignupStatus.confirmed}))
        _validate_projected_confirmed_costs(signup.session_id, storage, projected_confirmed)

        promoted = storage.update_signup(signup_id, SignupUpdate(status=SignupStatus.confirmed))
        _recalculate_session_costs(promoted.session_id, storage)
        return next(item for item in storage.get_signups(promoted.session_id) if item.id == signup_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signup not found") from exc


@router.delete("/signups/{signup_id}", response_model=Signup)
def cancel_signup(signup_id: str, storage: StorageAdapter = Depends(get_storage)) -> Signup:
    try:
        try:
            from .signups import _next_waitlisted_signup
        except ImportError:
            from routers.signups import _next_waitlisted_signup

        signup = _get_signup_by_id(storage, signup_id)
        session_id = signup.session_id
        was_confirmed = signup.status == SignupStatus.confirmed
        promoted = None
        if was_confirmed:
            courts = storage.get_courts(session_id)
            total_capacity = sum(court.max_players for court in courts)
            signups = storage.get_signups(session_id)
            confirmed_count = sum(1 for item in signups if item.status == SignupStatus.confirmed)
            if confirmed_count - 1 < total_capacity:
                waitlisted = sorted(
                    [item for item in signups if item.status == SignupStatus.waitlist],
                    key=lambda item: item.timestamp,
                )
                if waitlisted:
                    promoted = waitlisted[0]
            projected_confirmed = [
                item for item in signups
                if item.status == SignupStatus.confirmed and item.id != signup.id
            ]
            if promoted is not None:
                projected_confirmed.append(promoted.model_copy(update={"status": SignupStatus.confirmed}))
            if projected_confirmed:
                _validate_projected_confirmed_costs(session_id, storage, projected_confirmed)

        cancelled = storage.update_signup(
            signup_id,
            SignupUpdate(status=SignupStatus.cancelled, cancelled_at=datetime.now(timezone.utc)),
        )
        if promoted is not None:
            storage.update_signup(promoted.id, SignupUpdate(status=SignupStatus.confirmed))
        if was_confirmed and any(
            item.status == SignupStatus.confirmed for item in storage.get_signups(session_id)
        ):
            _recalculate_session_costs(session_id, storage)
        return cancelled
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
