from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

from routers import user, items, purchase
from utils.pid_assigner import PIDAssigner, SQLitePIDAssigner

PID_MATCHER_PATH = os.getenv("PID_MATCHER_PATH", "utils/pid_matcher.pkl")
PID_MATCHER_GCS = os.getenv("PID_MATCHER_GCS")
PID_MATCHER_SQLITE = os.getenv("PID_MATCHER_SQLITE")


def _download_from_gcs(gs_uri: str, dst_path: str) -> None:
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gs_uri}")

    bucket_name, blob_path = gs_uri.replace("gs://", "").split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_path).download_to_filename(dst_path)


def _resolve_matcher_path() -> Path:
    if PID_MATCHER_SQLITE:
        return Path(PID_MATCHER_SQLITE)

    path = Path(PID_MATCHER_PATH)
    if PID_MATCHER_GCS:
        suffix = Path(PID_MATCHER_GCS).suffix or path.suffix or ".pkl"
        return Path("/tmp") / f"pid_matcher{suffix}"
    return path

@asynccontextmanager
async def lifespan(app: FastAPI):
    matcher_path = _resolve_matcher_path()

    if PID_MATCHER_GCS:
        if not matcher_path.exists():
            _download_from_gcs(PID_MATCHER_GCS, str(matcher_path))

    if not matcher_path.exists():
        raise RuntimeError(f"PID matcher file not found: {matcher_path}")

    if matcher_path.suffix in (".sqlite", ".db"):
        app.state.pid_assigner = SQLitePIDAssigner(str(matcher_path))
    else:
        app.state.pid_assigner = PIDAssigner(str(matcher_path))
    yield



app = FastAPI(lifespan=lifespan)


app.include_router(user.router)
app.include_router(items.router)
app.include_router(purchase.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://hackathon-frontend-2i93y6emk-haruhisaasadas-projects.vercel.app",
    ],
    allow_origin_regex=r"https://hackathon-frontend-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
