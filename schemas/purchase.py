from pydantic import BaseModel

class PurchaseRequest(BaseModel):
    buyer_email: str
    buyer_username: str