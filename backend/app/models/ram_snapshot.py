from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class RamSnapshot(Base):
    """
    One row per RAM usage collection.
    Collected every 5 minutes by the agent.
    """
    __tablename__ = "ram_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    ram_used_gb = Column(Float, nullable=True)
    ram_available_gb = Column(Float, nullable=True)
    ram_percent_used = Column(Float, nullable=True)
