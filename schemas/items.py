from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    cat0: Optional[str] = None
    cat1: Optional[str] = None
    cat2: Optional[str] = None
    price: int
    image_path: Optional[str] = None

class ItemCreate(ItemBase):
    seller_email: str
    seller_username: str

#ItemUpdateは必要なら
class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    image_path: Optional[str] = None

class ItemResponse(ItemBase):
    item_id: int
    seller_email: str
    seller_username: str
    created_at: datetime
    class Config:
        orm_mode = True

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: Optional[str] = None

class UploadUrlResponse(BaseModel):
    upload_url: str
    public_url: str