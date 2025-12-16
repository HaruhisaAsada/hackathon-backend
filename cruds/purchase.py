from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.items import Item
from models.purchase_hist import PurchaseHist
from schemas.purchase import PurchaseRequest

def purchase_item(db: Session, item_id: int, req: PurchaseRequest):
    item = db.query(Item).filter(Item.item_id == item_id).with_for_update().first()
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
        sold_at=getattr(item, "sold_at", None),
    )
    db.add(hist)
    db.delete(item)
    db.commit()
    return {"ok": True, "message": "Purchased successfully"}
