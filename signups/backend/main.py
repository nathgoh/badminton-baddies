import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

try:
    from .auth import JWT_EXPIRE_HOURS, create_jwt, decode_jwt, verify_google_id_token
    from .middleware import require_admin
    from .routers import admin, signups, sessions
    from .storage.memory import InMemoryAdapter
except ImportError:
    from auth import JWT_EXPIRE_HOURS, create_jwt, decode_jwt, verify_google_id_token
    from middleware import require_admin
    from routers import admin, signups, sessions
    from storage.memory import InMemoryAdapter

load_dotenv()


class GoogleLoginRequest(BaseModel):
    id_token: str


def create_app() -> FastAPI:
    app = FastAPI(title="HBB Signups")

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    if os.getenv("USE_SHEETS", "false").lower() == "true":
        try:
            from .storage.sheets import SheetsAdapter
        except ImportError:
            from storage.sheets import SheetsAdapter

        app.state.storage = SheetsAdapter(
            spreadsheet_id=os.environ["SPREADSHEET_ID"],
            credentials_file=os.environ["GOOGLE_CREDENTIALS_FILE"],
        )
    else:
        app.state.storage = InMemoryAdapter()

    app.include_router(sessions.router, prefix="/api", dependencies=[Depends(require_admin)])
    app.include_router(signups.router, prefix="/api")
    app.include_router(admin.router, prefix="/api", dependencies=[Depends(require_admin)])

    @app.post("/auth/google")
    @limiter.limit("10/minute")
    def google_login(request: Request, body: GoogleLoginRequest) -> JSONResponse:
        try:
            payload = verify_google_id_token(body.id_token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="No email in token")
        if not app.state.storage.is_admin(email):
            raise HTTPException(status_code=403, detail="Not an admin")
        jwt_token = create_jwt(email)
        secure_cookie = os.getenv("COOKIE_SECURE", "true").lower() == "true"
        response = JSONResponse(content={"ok": True, "email": email})
        response.set_cookie(
            key="admin_token",
            value=jwt_token,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            max_age=JWT_EXPIRE_HOURS * 3600,
            path="/",
        )
        return response

    @app.post("/auth/logout")
    def logout() -> JSONResponse:
        response = JSONResponse(content={"ok": True})
        response.delete_cookie("admin_token", path="/")
        return response

    @app.get("/auth/me")
    def auth_me(request: Request) -> JSONResponse:
        token = request.cookies.get("admin_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        email = decode_jwt(token)
        if not email:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if not app.state.storage.is_admin(email):
            raise HTTPException(status_code=403, detail="Not an admin")
        return JSONResponse(content={"email": email})

    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    def robots() -> str:
        return "User-agent: *\nDisallow: /"

    dist_dir = os.path.join(os.path.dirname(__file__), 'dist')
    assets_dir = os.path.join(dist_dir, 'assets')
    index_file = os.path.join(dist_dir, 'index.html')
    if os.path.exists(assets_dir):
        app.mount('/assets', StaticFiles(directory=assets_dir), name='assets')

    if os.path.exists(index_file):
        @app.get('/{full_path:path}', include_in_schema=False)
        def serve_spa(full_path: str) -> FileResponse:
            return FileResponse(index_file)

    return app


app = create_app()
