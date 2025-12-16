from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db import Base

class PurchaseHist(Base):
    __tablename__ = "purchase_hist"

    purchase_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    item_id = Column(Integer, nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(String(255))
    cat0 = Column(String(255))
    cat1 = Column(String(255))
    cat2 = Column(String(255))
    price = Column(Integer, nullable=False)

    seller_email = Column(String(255), nullable=False)
    seller_username = Column(String(255), nullable=False)
    buyer_email = Column(String(255), nullable=False)
    buyer_username = Column(String(255), nullable=False)

    image_path = Column(String(255))
    sold_at = Column(DateTime(timezone=True), nullable=False)
    bought_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
