import os
from pathlib import Path
from datetime import datetime, timezone

from google.cloud import storage

from db import SessionLocal
from models.user import User
from cruds.purchase import update_recommendations
from utils.recommender import Recommender

REC_WV_GCS = os.getenv("REC_WV_GCS")
REC_LOCAL_PATH = os.getenv("REC_WV_PATH", "/tmp/item2vec_g4_w10.kv")
HISTORY_LIMIT = int(os.getenv("REC_HISTORY_LIMIT", "50"))
TOPN = int(os.getenv("REC_TOPN", "200"))


def _download_from_gcs(gs_uri: str, dst_path: str) -> None:
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gs_uri}")
    bucket_name, blob_path = gs_uri.replace("gs://", "").split("/", 1)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_path).download_to_filename(dst_path)


def _ensure_wv_path() -> Path:
    if REC_WV_GCS:
        path = Path(REC_LOCAL_PATH)
        if not path.exists():
            _download_from_gcs(REC_WV_GCS, str(path))
        return path
    return Path(REC_LOCAL_PATH)


def main() -> None:
    wv_path = _ensure_wv_path()
    if not wv_path.exists():
        raise RuntimeError(f"item2vec file not found: {wv_path}")

    recommender = Recommender(wv_kv_path=str(wv_path))

    db = SessionLocal()
    try:
        users = db.query(User.email).all()
        for (email,) in users:
            update_recommendations(
                db,
                email,
                recommender,
                history_limit=HISTORY_LIMIT,
                topn=TOPN,
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    started = datetime.now(timezone.utc)
    main()
    finished = datetime.now(timezone.utc)
    print(f"[batch] completed: {started.isoformat()} -> {finished.isoformat()}")
