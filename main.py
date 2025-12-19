from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

from routers import user, items, purchase
from utils.pid_assigner import PIDAssigner, SQLitePIDAssigner
from utils.recommender import Recommender

PID_MATCHER_PATH = os.getenv("PID_MATCHER_PATH", "utils/pid_matcher.pkl")
PID_MATCHER_GCS = os.getenv("PID_MATCHER_GCS")
PID_MATCHER_SQLITE = os.getenv("PID_MATCHER_SQLITE")

REC_WV_GCS = os.getenv("REC_WV_GCS")
REC_LIFT_GCS = os.getenv("REC_LIFT_GCS")
REC_POPULAR_GCS = os.getenv("REC_POPULAR_GCS")
REC_GRU_GCS = os.getenv("REC_GRU_GCS")


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

def _resolve_rec_path(gs_uri: str, fallback_name: str) -> Path:
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gs_uri}")
    suffix = Path(gs_uri).suffix or Path(fallback_name).suffix
    return Path("/tmp") / f"{fallback_name}{suffix}"

def _ensure_recommender_artifacts() -> dict[str, Path]:
    any_set = any([REC_WV_GCS, REC_LIFT_GCS, REC_POPULAR_GCS, REC_GRU_GCS])
    if any_set and not (REC_WV_GCS and REC_LIFT_GCS and REC_POPULAR_GCS and REC_GRU_GCS):
        raise RuntimeError("REC_*_GCS must all be set to enable recommender")
    if not (REC_WV_GCS and REC_LIFT_GCS and REC_POPULAR_GCS and REC_GRU_GCS):
        return {}
    paths = {
        "wv": _resolve_rec_path(REC_WV_GCS, "item2vec_g4_w10.kv"),
        "lift": _resolve_rec_path(REC_LIFT_GCS, "lift_dict.pkl"),
        "popular": _resolve_rec_path(REC_POPULAR_GCS, "popular_pids.pkl"),
        "gru": _resolve_rec_path(REC_GRU_GCS, "gru_reranker.pt"),
    }
    if not paths["wv"].exists():
        _download_from_gcs(REC_WV_GCS, str(paths["wv"]))
    if not paths["lift"].exists():
        _download_from_gcs(REC_LIFT_GCS, str(paths["lift"]))
    if not paths["popular"].exists():
        _download_from_gcs(REC_POPULAR_GCS, str(paths["popular"]))
    if not paths["gru"].exists():
        _download_from_gcs(REC_GRU_GCS, str(paths["gru"]))
    return paths

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

    rec_paths = _ensure_recommender_artifacts()
    if rec_paths:
        app.state.recommender = Recommender(
            wv_kv_path=str(rec_paths["wv"]),
            lift_dict_path=str(rec_paths["lift"]),
            popular_pkl_path=str(rec_paths["popular"]),
            gru_ckpt_path=str(rec_paths["gru"]),
            device="cpu",
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
        "https://hackathon-frontend-2i93y6emk-haruhisaasadas-projects.vercel.app",
    ],
    allow_origin_regex=r"https://hackathon-frontend-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
