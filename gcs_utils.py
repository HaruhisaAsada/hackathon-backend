import os
import uuid
import mimetypes
import logging
from datetime import timedelta
from fastapi import HTTPException

from google.cloud import storage
import google.auth
from google.auth import iam
from google.auth.transport.requests import Request as AuthRequest

logger = logging.getLogger("gcs_utils")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def _must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"環境変数 {name} が設定されていません")
    return v


def generate_upload_signed_url(filename: str, content_type: str | None = None) -> tuple[str, str]:
    logger.info(f"[gcs_utils] start filename={filename!r} content_type={content_type!r}")

    lower = (filename or "").lower()
    if not (lower.endswith(".jpg") or lower.endswith(".jpeg")):
        raise HTTPException(status_code=400, detail="JPEG画像のみアップロード可能です（.jpg/.jpeg）")

    bucket_name = _must_env("GCS_BUCKET_NAME")
    sa_email = _must_env("GCP_SERVICE_ACCOUNT_EMAIL")

    # GCS上は拡張子 .jpg 固定（中身は jpeg）
    object_name = f"items/{uuid.uuid4()}.jpg"

    if content_type is None:
        guessed = mimetypes.guess_type(filename)[0]
        content_type = guessed or "image/jpeg"

    # ★Cloud Run のデフォルト認証（トークン）を使って IAM Credentials API で署名する
    base_credentials, _ = google.auth.default()
    req = AuthRequest()
    base_credentials.refresh(req)

    signer = iam.Signer(
        request=req,
        credentials=base_credentials,
        service_account_email=sa_email,
    )

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    logger.info("[gcs_utils] generating signed url via IAM Signer...")
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=5),
        method="PUT",
        content_type=content_type,
        credentials=signer,  # ← signer を渡すのがポイント
    )
    logger.info("[gcs_utils] signed url OK")

    public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
    logger.info(f"[gcs_utils] done public_url={public_url}")
    return upload_url, public_url
