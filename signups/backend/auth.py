import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


def get_google_client_id() -> str:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID environment variable is not set")
    return client_id


def verify_google_id_token(token: str) -> dict:
    try:
        return id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            get_google_client_id(),
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google ID token: {exc}") from exc


def create_jwt(email: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": email, "exp": expire},
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_jwt(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

