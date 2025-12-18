from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from db import get_db
from schemas.items import (ItemCreate, ItemResponse, UploadUrlRequest, UploadUrlResponse)
from cruds import items
from cruds.items import get_items, get_item_by_id
from models.items import Item
from gcs_utils import generate_upload_signed_url
from utils.embeddings import gemini_embed, vec_to_string_to_vector_arg

router = APIRouter()

@router.get("/items", response_model=list[ItemResponse])
async def read_items(db: Session = Depends(get_db)):
    return await run_in_threadpool(get_items, db)

@router.get("/items/{item_id}", response_model=ItemResponse)
async def read_item(item_id: int, db: Session = Depends(get_db)):
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

@router.delete("/items/{item_id}", response_model=ItemResponse)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    deleted = await run_in_threadpool(items.delete_item, db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return deleted

@router.get("/items/search")
async def search_items(q: str, k: int = 30, db: Session = Depends(get_db)):
    # 1) クエリを埋め込み
    qvec = await run_in_threadpool(gemini_embed, q, task_type="RETRIEVAL_QUERY", dims=768)
    qvec_str = vec_to_string_to_vector_arg(qvec)

    # 2) ベクトル検索（distが小さいほど近い）
    sql = text("""
        SELECT item_id, name, description, cat0, cat1, cat2, price, image_path,
                cosine_distance(string_to_vector(:qvec), embedding) AS dist
        FROM items
        WHERE embedding IS NOT NULL
        ORDER BY dist
        LIMIT :k
    """)
    rows = db.execute(sql, {"qvec": qvec_str, "k": k}).mappings().all()
    return list(rows)

@router.post("/admin/backfill-embeddings")
async def backfill_embeddings(limit: int = 20, db: Session = Depends(get_db)):
    # 1) NULLの行を取る
    items_ = db.execute(text("""
        SELECT item_id, name,
                COALESCE(description,'') AS description,
                COALESCE(cat0,'') AS cat0,
                COALESCE(cat1,'') AS cat1,
                COALESCE(cat2,'') AS cat2
        FROM items
        WHERE embedding IS NULL
        LIMIT :limit
    """), {"limit": limit}).mappings().all()

    updated = 0
    for it in items_:
        doc = f"{it['name']}\n{it['description']}\nカテゴリ: {it['cat0']}/{it['cat1']}/{it['cat2']}"
        vec = await run_in_threadpool(gemini_embed, doc, task_type="RETRIEVAL_DOCUMENT", dims=768)
        vstr = vec_to_string_to_vector_arg(vec)

        db.execute(text("""
            UPDATE items
            SET embedding = string_to_vector(:v)
            WHERE item_id = :id
        """), {"v": vstr, "id": it["item_id"]})
        updated += 1

    db.commit()
    return {"updated": updated}

