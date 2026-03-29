from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload, video, detect, analyze, tus

app = FastAPI(title="Badminton Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(tus.router)
app.include_router(video.router)
app.include_router(detect.router)
app.include_router(analyze.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
