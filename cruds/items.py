from sqlalchemy.orm import Session, defer
from typing import List, Optional
from models.items import Item
from schemas.items import ItemCreate, ItemUpdate
from sqlalchemy import text
from utils.embeddings import gemini_embed, vec_to_string_to_vector_arg

def get_items(db: Session):
    return db.query(Item).options(defer(Item.embedding)).all()

def get_item_by_id(db: Session, item_id: str):
    return (
        db.query(Item)
        .options(defer(Item.embedding))
        .filter(Item.item_id == item_id)
        .first()
    )


def get_items_by_seller(
    db: Session, seller_email: str, skip: int = 0, limit: int = 20
) -> List[Item]:
    return (
        db.query(Item)
        .options(defer(Item.embedding))
        .filter(Item.seller_email == seller_email)
        .order_by(Item.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_item(db: Session, item: ItemCreate, pid=None) -> Item:
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
        pid=pid,
    )
    db.add(db_item)
    db.flush()
    item_id = db_item.item_id
    doc = (
        f"{item.name}\n"
        f"{item.description or ''}\n"
        f"カテゴリ: {item.cat0 or ''}/{item.cat1 or ''}/{item.cat2 or ''}"
    )
    db.commit()
    try:
        vec = gemini_embed(doc, task_type="RETRIEVAL_DOCUMENT", dims=768)
        vstr = vec_to_string_to_vector_arg(vec)

        db.execute(
            text("""
                UPDATE items
                SET embedding = string_to_vector(:v)
                WHERE item_id = :id
            """),
            {"v": vstr, "id": item_id},
        )
        db.commit()
    except Exception:
        #埋め込みに失敗しても出品はする
        db.rollback()

    return get_item_by_id(db, item_id) or db_item


def delete_item(db: Session, item_id: int) -> Optional[Item]:
    item = (
        db.query(Item)
        .options(defer(Item.embedding))
        .filter(Item.item_id == item_id)
        .first()
    )
    if item is None:
        return None
    db.delete(item)
    db.commit()
    return item
