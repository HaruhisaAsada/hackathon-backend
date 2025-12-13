import os
import uuid
import mimetypes
from datetime import timedelta
from fastapi import HTTPException
from schemas.items import UploadUrlRequest

from google.cloud import storage


BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")


def get_storage_client() -> storage.Client:
    return storage.Client()


def generate_upload_signed_url(filename: str, content_type: str | None = None) -> tuple[str, str]:
    if not filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="JPEG画像のみアップロード可能です")
    if BUCKET_NAME is None:
        raise RuntimeError("環境変数 GCS_BUCKET_NAME が設定されていません")

    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)

    # ファイル名から拡張子を取得しておく（image.jpg など）
    ext = os.path.splitext(filename)[1]  # ".jpg" など
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
    )

    # ブラウザからアクセスするときに使う URL（公開バケットならそのままアクセス可）
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"

    return upload_url, public_url
