import os
import uuid
import mimetypes
import logging
from datetime import timedelta
from fastapi import HTTPException

from google.cloud import storage

logger = logging.getLogger("gcs_utils")
# Uvicorn/FastAPI のログ設定に従う。念のため最低限の設定も入れる（重複しても実害ほぼなし）
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def get_storage_client() -> storage.Client:
    logger.info("[gcs_utils] get_storage_client: creating storage.Client()")
    client = storage.Client()
    logger.info("[gcs_utils] get_storage_client: created storage.Client() OK")
    return client


def _env(name: str) -> str:
    """必須 env を取り出し、無ければ 500 ではなく分かりやすい例外にする"""
    v = os.getenv(name)
    logger.info(f"[gcs_utils] env: {name}={'(set)' if v else '(missing)'}")
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def generate_upload_signed_url(filename: str, content_type: str | None = None) -> tuple[str, str]:
    logger.info(f"[gcs_utils] generate_upload_signed_url: start filename={filename!r} content_type={content_type!r}")

    # 1) 入力チェック（jpg/jpeg のみに固定）
    lower = (filename or "").lower()
    if not (lower.endswith(".jpg") or lower.endswith(".jpeg")):
        logger.warning(f"[gcs_utils] invalid extension: {filename!r}")
        raise HTTPException(status_code=400, detail="JPEG画像のみアップロード可能です（.jpg / .jpeg）")

    # 2) 環境変数チェック
    bucket_name = _env("GCP_GCS_BUCKET_NAME")
    sa_email = _env("GCP_SERVICE_ACCOUNT_EMAIL")

    # 3) GCS クライアント作成
    try:
        client = get_storage_client()
    except Exception as e:
        logger.exception("[gcs_utils] failed to create storage.Client()")
        raise

    # 4) バケット取得
    logger.info(f"[gcs_utils] bucket: getting bucket name={bucket_name!r}")
    bucket = client.bucket(bucket_name)
    logger.info("[gcs_utils] bucket: got bucket object OK")

    # 5) オブジェクト名生成（拡張子を .jpg に固定）
    object_name = f"items/{uuid.uuid4()}.jpg"
    logger.info(f"[gcs_utils] object_name: {object_name}")

    blob = bucket.blob(object_name)
    logger.info("[gcs_utils] blob: created blob object OK")

    # 6) Content-Type 決定（未指定なら jpg に寄せる）
    if content_type is None:
        guessed = mimetypes.guess_type(filename)[0]
        content_type = guessed or "image/jpeg"
        logger.info(f"[gcs_utils] content_type: guessed={guessed!r} -> use={content_type!r}")
    else:
        logger.info(f"[gcs_utils] content_type: provided={content_type!r}")

    # 7) 署名付きURL生成（ここが落ちやすいので try/except でログ厚め）
    logger.info("[gcs_utils] generate_signed_url: start (v4, PUT)")
    try:
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=5),
            method="PUT",
            content_type=content_type,
            service_account_email=sa_email,
        )
        logger.info("[gcs_utils] generate_signed_url: success")
    except Exception as e:
        logger.exception("[gcs_utils] generate_signed_url: FAILED")
        # ここで落ちると /items/upload-url が 500 になる。ログの traceback が主犯。
        raise

    # 8) 公開URL生成（バケット名も env と一致させる）
    public_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
    logger.info(f"[gcs_utils] public_url: {public_url}")

    logger.info("[gcs_utils] generate_upload_signed_url: done")
    return upload_url, public_url
