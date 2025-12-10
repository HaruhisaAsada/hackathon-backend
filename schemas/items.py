from pydantic import BaseModel

class ItemBase(BaseModel):
    item_id: int
    name: str
    price: int
    seller_email: str
    seller_username: str
    image_path: str | None = None

class ItemResponse(ItemBase):
    class Config:
        orm_mode = True
