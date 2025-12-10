from sqlalchemy.orm import Session
from models.items import Item

def get_items(db: Session):
    return db.query(Item).all()

def get_item_by_id(db: Session, item_id: str):
    return db.query(Item).filter(Item.item_id == item_id).first()
