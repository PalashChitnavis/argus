from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class OneMinuteData(Base):
    __tablename__ = "one_minute_data"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    cpu_percent_used = Column(Float, nullable=True)

    new_processes = relationship(
        "NewProcess",
        back_populates="one_minute_data",
        cascade="all, delete-orphan"
    )