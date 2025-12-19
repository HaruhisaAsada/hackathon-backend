from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

from routers import user, items, purchase
from db import engine
from utils.pid_assigner import PIDAssigner, SQLitePIDAssigner, MySQLPIDAssigner, LazyPIDAssigner

PID_MATCHER_PATH = os.getenv("PID_MATCHER_PATH", "utils/pid_matcher.pkl")
PID_MATCHER_GCS = os.getenv("PID_MATCHER_GCS")
PID_MATCHER_SQLITE = os.getenv("PID_MATCHER_SQLITE")
PID_MATCHER_MYSQL = os.getenv("PID_MATCHER_MYSQL", "false").lower() in ("1", "true", "yes")
PID_MAX_CANDIDATES = int(os.getenv("PID_MAX_CANDIDATES", "3000"))
PID_MAX_TOKENS = int(os.getenv("PID_MAX_TOKENS", "12"))
PID_TOKEN_LIMIT = int(os.getenv("PID_TOKEN_LIMIT", "200"))

REC_WV_GCS = os.getenv("REC_WV_GCS")
REC_LOAD_ON_STARTUP = os.getenv("REC_LOAD_ON_STARTUP", "false").lower() in ("1", "true", "yes")


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


def _ensure_matcher_file(matcher_path: Path) -> None:
    if matcher_path.exists():
        return
    if not PID_MATCHER_GCS:
        return
    _download_from_gcs(PID_MATCHER_GCS, str(matcher_path))

def _resolve_rec_path(gs_uri: str, fallback_name: str) -> Path:
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gs_uri}")
    suffix = Path(gs_uri).suffix or Path(fallback_name).suffix
    return Path("/tmp") / f"{fallback_name}{suffix}"

def _ensure_recommender_artifacts() -> dict[str, Path]:
    if not REC_WV_GCS:
        return {}
    paths = {
        "wv": _resolve_rec_path(REC_WV_GCS, "item2vec_g4_w10.kv"),
    }
    if not paths["wv"].exists():
        _download_from_gcs(REC_WV_GCS, str(paths["wv"]))
    return paths

def _build_pid_assigner():
    if PID_MATCHER_MYSQL:
        return MySQLPIDAssigner(
            engine,
            max_candidates=PID_MAX_CANDIDATES,
            max_tokens=PID_MAX_TOKENS,
            token_limit=PID_TOKEN_LIMIT,
        )

    matcher_path = _resolve_matcher_path()
    _ensure_matcher_file(matcher_path)
    if not matcher_path.exists():
        raise RuntimeError(f"PID matcher file not found: {matcher_path}")

    if matcher_path.suffix in (".sqlite", ".db"):
        return SQLitePIDAssigner(
            str(matcher_path),
            max_candidates=PID_MAX_CANDIDATES,
            max_tokens=PID_MAX_TOKENS,
            token_limit=PID_TOKEN_LIMIT,
        )
    return PIDAssigner(
        str(matcher_path),
        max_candidates=PID_MAX_CANDIDATES,
        max_tokens=PID_MAX_TOKENS,
        token_limit=PID_TOKEN_LIMIT,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pid_assigner = LazyPIDAssigner(_build_pid_assigner)

    if REC_LOAD_ON_STARTUP:
        from utils.recommender import Recommender
        rec_paths = _ensure_recommender_artifacts()
        if rec_paths:
            app.state.recommender = Recommender(
                wv_kv_path=str(rec_paths["wv"]),
            )
    yield



app = FastAPI(lifespan=lifespan)


app.include_router(user.router)
app.include_router(items.router)
app.include_router(purchase.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://hackathon-frontend-ecq0ty9fs-haruhisaasadas-projects.vercel.app",
    ],
    allow_origin_regex=r"https://hackathon-frontend-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
