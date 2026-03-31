from fastapi import APIRouter, Depends, HTTPException, Response, status

try:
    from ..dependencies import get_storage
    from ..models import Court, CourtCreate, CourtUpdate, Session, SessionCreate, SessionUpdate, SignupStatus
    from ..storage.adapter import StorageAdapter
    from .admin import _recalculate_session_costs
except ImportError:
    from dependencies import get_storage
    from models import Court, CourtCreate, CourtUpdate, Session, SessionCreate, SessionUpdate, SignupStatus
    from storage.adapter import StorageAdapter
    from routers.admin import _recalculate_session_costs


router = APIRouter()


def _get_court_by_id(storage: StorageAdapter, court_id: str) -> Court:
    for session in storage.list_sessions():
        court = next((item for item in storage.get_courts(session.id) if item.id == court_id), None)
        if court is not None:
            return court
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court not found")


def _has_confirmed_signups(session_id: str, storage: StorageAdapter) -> bool:
    return any(
        signup.status == SignupStatus.confirmed for signup in storage.get_signups(session_id)
    )


def _validate_projected_court_total_cost(
    session_id: str, storage: StorageAdapter, projected_total_cost: float
) -> None:
    confirmed = [
        signup for signup in storage.get_signups(session_id) if signup.status == SignupStatus.confirmed
    ]
    if not confirmed:
        return

    adjusted_total = round(
        sum(signup.amount_owed for signup in confirmed if signup.amount_adjusted and signup.amount_owed is not None),
        2,
    )
    if adjusted_total > round(projected_total_cost, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjusted amounts (${adjusted_total:.2f}) exceed total cost (${projected_total_cost:.2f})",
        )


@router.get("/sessions", response_model=list[Session])
def list_sessions(storage: StorageAdapter = Depends(get_storage)) -> list[Session]:
    return storage.list_sessions()


@router.post("/sessions", response_model=Session, status_code=status.HTTP_201_CREATED)
def create_session(
    data: SessionCreate, storage: StorageAdapter = Depends(get_storage)
) -> Session:
    return storage.create_session(data)


@router.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str, storage: StorageAdapter = Depends(get_storage)) -> Session:
    session = next((item for item in storage.list_sessions() if item.id == session_id), None)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=Session)
def update_session(
    session_id: str,
    data: SessionUpdate,
    storage: StorageAdapter = Depends(get_storage),
) -> Session:
    try:
        return storage.update_session(session_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str, storage: StorageAdapter = Depends(get_storage)
) -> Response:
    try:
        storage.delete_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions/{session_id}/courts", response_model=list[Court])
def get_courts(session_id: str, storage: StorageAdapter = Depends(get_storage)) -> list[Court]:
    return storage.get_courts(session_id)


@router.post("/sessions/{session_id}/courts", response_model=Court, status_code=status.HTTP_201_CREATED)
def create_court(
    session_id: str,
    data: CourtCreate,
    storage: StorageAdapter = Depends(get_storage),
) -> Court:
    payload = CourtCreate(session_id=session_id, **data.model_dump(exclude={"session_id"}))
    court = storage.create_court(payload)
    if _has_confirmed_signups(session_id, storage):
        _recalculate_session_costs(session_id, storage)
    return court


@router.patch("/courts/{court_id}", response_model=Court)
def update_court(
    court_id: str, data: CourtUpdate, storage: StorageAdapter = Depends(get_storage)
) -> Court:
    court = _get_court_by_id(storage, court_id)
    if _has_confirmed_signups(court.session_id, storage):
        current_total_cost = sum(item.total_cost for item in storage.get_courts(court.session_id))
        projected_total_cost = current_total_cost - court.total_cost + (
            data.total_cost if data.total_cost is not None else court.total_cost
        )
        _validate_projected_court_total_cost(court.session_id, storage, projected_total_cost)

    try:
        court = storage.update_court(court_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court not found") from exc
    if _has_confirmed_signups(court.session_id, storage):
        _recalculate_session_costs(court.session_id, storage)
    return court


@router.delete("/courts/{court_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_court(court_id: str, storage: StorageAdapter = Depends(get_storage)) -> Response:
    court = _get_court_by_id(storage, court_id)
    if _has_confirmed_signups(court.session_id, storage):
        current_total_cost = sum(item.total_cost for item in storage.get_courts(court.session_id))
        projected_total_cost = current_total_cost - court.total_cost
        _validate_projected_court_total_cost(court.session_id, storage, projected_total_cost)
    storage.delete_court(court_id)
    if _has_confirmed_signups(court.session_id, storage):
        _recalculate_session_costs(court.session_id, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
