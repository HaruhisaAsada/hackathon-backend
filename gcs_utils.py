import os
import uuid
import mimetypes
from datetime import timedelta
from fastapi import HTTPException
from schemas.items import UploadUrlRequest

from google.cloud import storage


def get_storage_client() -> storage.Client:
    return storage.Client()


def generate_upload_signed_url(filename: str, content_type: str | None = None) -> tuple[str, str]:
    if not filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="JPEG画像のみアップロード可能です")

    client = get_storage_client()
    bucket = client.bucket("fleamarketapp")

    # ファイル名から拡張子を取得しておく（image.jpg など）
    ext = os.path.splitext(filename)[1]
    # GCS 上のオブジェクト名（重複防止に UUID を付ける）
    object_name = f"items/{uuid.uuid4()}{ext}"

    blob = bucket.blob(object_name)

    # Content-Type が未指定なら拡張子から推定
    if content_type is None:
        guessed = mimetypes.guess_type(filename)[0]
        content_type = guessed or "application/octet-stream"

    # 署名付き URL を発行（PUT 用）
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=5),
        method="PUT",
        content_type=content_type,
        service_account_email=os.getenv("GCP_SERVICE_ACCOUNT_EMAIL"),
    )

    # ブラウザからアクセスするときに使う URL（公開バケットならそのままアクセス可）
    public_url = f"https://storage.googleapis.com/fleamarketapp/{object_name}"

    return upload_url, public_url
