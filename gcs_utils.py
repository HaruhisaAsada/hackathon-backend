import os
import uuid
import mimetypes
import logging
from datetime import timedelta
from fastapi import HTTPException

from google.cloud import storage
import google.auth
from google.auth import impersonated_credentials

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
    target_sa = _must_env("GCP_SERVICE_ACCOUNT_EMAIL")

    # GCS上は .jpg 固定
    object_name = f"items/{uuid.uuid4()}.jpg"

    if content_type is None:
        guessed = mimetypes.guess_type(filename)[0]
        content_type = guessed or "image/jpeg"

    source_credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    signing_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_sa,
        target_scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        lifetime=300,
    )

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    logger.info("[gcs_utils] generating signed url via impersonated_credentials...")
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=5),
        method="PUT",
        content_type=content_type,
        credentials=signing_credentials,
    )

    public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
    logger.info(f"[gcs_utils] done public_url={public_url}")
    return upload_url, public_url
