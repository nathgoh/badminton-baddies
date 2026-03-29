from fastapi import APIRouter, Depends, HTTPException, Response, status

try:
    from ..dependencies import get_storage
    from ..models import Court, CourtCreate, CourtUpdate, Session, SessionCreate, SessionUpdate
    from ..storage.adapter import StorageAdapter
except ImportError:
    from dependencies import get_storage
    from models import Court, CourtCreate, CourtUpdate, Session, SessionCreate, SessionUpdate
    from storage.adapter import StorageAdapter


router = APIRouter()


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
    return storage.create_court(payload)


@router.patch("/courts/{court_id}", response_model=Court)
def update_court(
    court_id: str, data: CourtUpdate, storage: StorageAdapter = Depends(get_storage)
) -> Court:
    try:
        return storage.update_court(court_id, data)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court not found") from exc


@router.delete("/courts/{court_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_court(court_id: str, storage: StorageAdapter = Depends(get_storage)) -> Response:
    try:
        storage.delete_court(court_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

