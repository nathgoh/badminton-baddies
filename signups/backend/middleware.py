from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from .auth import decode_jwt
    from .dependencies import get_storage
    from .storage.adapter import StorageAdapter
except ImportError:
    from auth import decode_jwt
    from dependencies import get_storage
    from storage.adapter import StorageAdapter


bearer_scheme = HTTPBearer()


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    storage: StorageAdapter = Depends(get_storage),
) -> str:
    email = decode_jwt(credentials.credentials)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if not storage.is_admin(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin")
    return email

