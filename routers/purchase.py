from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from db import get_db
from schemas.purchase import PurchaseRequest, PurchaseHistResponse
from cruds.purchase import purchase_item, get_purchase_history

router = APIRouter(tags=["purchase"])

@router.post("/purchase/{item_id}")
async def purchase(
    item_id: int,
    req: PurchaseRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        recommender = getattr(request.app.state, "recommender", None)
        return await run_in_threadpool(purchase_item, db, item_id, req, recommender)
    except Exception:
        db.rollback()
        raise

@router.get("/purchase-history", response_model=list[PurchaseHistResponse])
async def purchase_history(buyer_email: str, db: Session = Depends(get_db)):
    try:
        return await run_in_threadpool(get_purchase_history, db, buyer_email)
    except Exception:
        db.rollback()
        raise
