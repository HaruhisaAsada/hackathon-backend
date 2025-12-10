from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from db import get_db
from schemas.items import ItemResponse
from cruds.items import get_items, get_item_by_id

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
