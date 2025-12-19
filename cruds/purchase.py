from sqlalchemy.orm import Session, defer
from fastapi import HTTPException
from models.items import Item
from models.purchase_hist import PurchaseHist
from models.user import User
from schemas.purchase import PurchaseRequest
from typing import List, Optional
from datetime import datetime, timezone

def purchase_item(db: Session, item_id: int, req: PurchaseRequest):
    item = (
        db.query(Item)
        .options(defer(Item.embedding))
        .filter(Item.item_id == item_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found (maybe already sold)")

    hist = PurchaseHist(
        item_id=item.item_id,
        name=item.name,
        description=item.description,
        cat0=item.cat0,
        cat1=item.cat1,
        cat2=item.cat2,
        price=item.price,
        seller_email=item.seller_email,
        seller_username=item.seller_username,
        buyer_email=req.buyer_email,
        buyer_username=req.buyer_username,
        image_path=item.image_path,
        sold_at=item.created_at,
        bought_at=datetime.now(timezone.utc),
        pid=item.pid,
    )
    db.add(hist)
    db.delete(item)
    db.commit()
    return {"ok": True, "message": "Purchased successfully"}

def get_purchase_history(db: Session, buyer_email: str, limit: int = 100) -> List[PurchaseHist]:
    return (
        db.query(PurchaseHist)
        .filter(PurchaseHist.buyer_email == buyer_email)
        .order_by(PurchaseHist.bought_at.desc())
        .limit(limit)
        .all()
    )

def get_recent_purchase_item_ids(db: Session, buyer_email: str, limit: int = 20) -> list[int]:
    rows = (
        db.query(PurchaseHist.pid)
        .filter(PurchaseHist.buyer_email == buyer_email)
        .order_by(PurchaseHist.bought_at.desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]

def update_recommendations(
    db: Session,
    buyer_email: str,
    recommender: Optional[object],
    *,
    history_limit: int = 50,
    topn: int = 200,
) -> None:
    if recommender is None:
        return
    hist_pids = get_recent_purchase_item_ids(db, buyer_email, limit=history_limit)
    if not hist_pids:
        return
    history = [str(pid) for pid in hist_pids if pid]
    ranked = recommender.recommend(history, topn=topn)
    rec_pids = [pid for pid, _ in ranked]
    user = db.query(User).filter(User.email == buyer_email).first()
    if not user:
        return
    user.rec_pids = rec_pids
    user.rec_updated_at = datetime.now(timezone.utc)
    db.commit()
