from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List
from db import get_db
from schemas.items import (ItemCreate, ItemResponse, UploadUrlRequest, UploadUrlResponse)
from cruds import items
from cruds.items import get_items, get_item_by_id
from models.items import Item
from gcs_utils import generate_upload_signed_url

router = APIRouter()

@router.get("/items", response_model=list[ItemResponse])
async def read_items(db: Session = Depends(get_db)):
    return await run_in_threadpool(get_items, db)

@router.get("/items/{item_id}", response_model=ItemResponse)
async def read_item(item_id: str, db: Session = Depends(get_db)):
    item = await run_in_threadpool(get_item_by_id, db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/items", response_model=ItemResponse)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    return await run_in_threadpool(items.create_item, db, item)

@router.post("/items/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(payload: UploadUrlRequest):
    if not payload.filename.lower().endswith((".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="JPEG画像のみアップロード可能です")
    upload_url, public_url = await run_in_threadpool(
        generate_upload_signed_url,
        filename=payload.filename,
        content_type=payload.content_type,
    )
    return {"upload_url": upload_url, "public_url": public_url}