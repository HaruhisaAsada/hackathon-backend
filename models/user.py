from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from db import Base

class User(Base):
    __tablename__ = "users"

    email = Column(String(255), primary_key=True, index=True)
    username = Column(String(26), unique=True, nullable=False)
    introduction = Column(String(511), nullable=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rec_pids = Column(JSON, nullable=True)
    rec_updated_at = Column(DateTime(timezone=True), nullable=True)

