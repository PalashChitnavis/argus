from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, unique=True, nullable=False, index=True)
    hostname = Column(String, nullable=False)
    api_key_hash = Column(String, unique=True, nullable=False, index=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())