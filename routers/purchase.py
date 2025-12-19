from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from db import get_db
from schemas.purchase import PurchaseRequest, PurchaseHistResponse
from cruds.purchase import purchase_item, get_purchase_history, update_recommendations

router = APIRouter(tags=["purchase"])

@router.post("/purchase/{item_id}")
async def purchase(item_id: int, req: PurchaseRequest, request: Request, db: Session = Depends(get_db)):
    try:
        result = await run_in_threadpool(purchase_item, db, item_id, req)
        recommender = getattr(request.app.state, "recommender", None)
        if recommender is not None:
            await run_in_threadpool(update_recommendations, db, req.buyer_email, recommender)
        return result
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
