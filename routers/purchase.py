from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db
from schemas.purchase import PurchaseRequest
from cruds.purchase import purchase_item

router = APIRouter(tags=["purchase"])

@router.post("/purchase/{item_id}")
def purchase(item_id: int, req: PurchaseRequest, db: Session = Depends(get_db)):
    try:
        return purchase_item(db, item_id, req)
    except Exception:
        db.rollback()
        raise
