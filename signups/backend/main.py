import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from .auth import create_jwt, verify_google_id_token
    from .middleware import require_admin
    from .routers import admin, signups, sessions
    from .storage.memory import InMemoryAdapter
except ImportError:
    from auth import create_jwt, verify_google_id_token
    from middleware import require_admin
    from routers import admin, signups, sessions
    from storage.memory import InMemoryAdapter

load_dotenv()


class GoogleLoginRequest(BaseModel):
    id_token: str


def create_app() -> FastAPI:
    app = FastAPI(title="HBB Signups")

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
    def google_login(body: GoogleLoginRequest) -> dict[str, str]:
        try:
            payload = verify_google_id_token(body.id_token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="No email in token")
        if not app.state.storage.is_admin(email):
            raise HTTPException(status_code=403, detail="Not an admin")
        return {"access_token": create_jwt(email), "email": email}

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
