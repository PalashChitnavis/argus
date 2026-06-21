from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    token = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used = Column(Boolean, default=False, nullable=False)
    used_by_node_id = Column(Integer, ForeignKey("nodes.id"), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)