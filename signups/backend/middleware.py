from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from .auth import decode_jwt
    from .dependencies import get_storage
    from .storage.adapter import StorageAdapter
except ImportError:
    from auth import decode_jwt
    from dependencies import get_storage
    from storage.adapter import StorageAdapter


bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    storage: StorageAdapter = Depends(get_storage),
) -> str:
    # Prefer httpOnly cookie; fall back to Bearer header for compatibility
    token: Optional[str] = request.cookies.get("admin_token")
    if not token and credentials:
        token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    email = decode_jwt(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if not storage.is_admin(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin")
    return email

