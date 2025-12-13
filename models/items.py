from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from db import Base

class Item(Base):
    __tablename__ = "items"

    item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    cat0 = Column(String(255))
    cat1 = Column(String(255))
    cat2 = Column(String(255))
    price = Column(Integer, nullable=False)
    seller_email = Column(String(255), nullable=False)
    seller_username = Column(String(255), nullable=False)
    image_path = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())