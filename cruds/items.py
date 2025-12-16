from sqlalchemy.orm import Session
from typing import List, Optional
from models.items import Item
from schemas.items import ItemCreate, ItemUpdate

def get_items(db: Session):
    return db.query(Item).all()

def get_item_by_id(db: Session, item_id: str):
    return db.query(Item).filter(Item.item_id == item_id).first()


def get_items_by_seller(
    db: Session, seller_email: str, skip: int = 0, limit: int = 20
) -> List[Item]:
    return (
        db.query(Item)
        .filter(Item.seller_email == seller_email)
        .order_by(Item.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_item(db: Session, item: ItemCreate) -> Item:
    db_item = Item(
        name=item.name,
        description=item.description,
        cat0=item.cat0,
        cat1=item.cat1,
        cat2=item.cat2,
        price=item.price,
        seller_email=item.seller_email,
        seller_username=item.seller_username,
        image_path=item.image_path,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int) -> Optional[Item]:
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if item is None:
        return None
    db.delete(item)
    db.commit()
    return item