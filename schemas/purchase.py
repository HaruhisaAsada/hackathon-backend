from pydantic import BaseModel, ConfigDict
from datetime import datetime

class PurchaseRequest(BaseModel):
    buyer_email: str
    buyer_username: str

class PurchaseHistResponse(BaseModel):
    purchase_id: int
    item_id: int
    name: str
    description: str | None = None
    cat0: str | None = None
    cat1: str | None = None
    cat2: str | None = None
    price: int
    seller_email: str
    seller_username: str
    buyer_email: str
    buyer_username: str
    image_path: str | None = None
    sold_at: datetime | None = None
    bought_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)