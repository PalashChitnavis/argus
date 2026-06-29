from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class DiskSnapshot(Base):
    """
    One row per disk usage collection.
    Collected every 5 minutes by the agent.
    """
    __tablename__ = "disk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    disk_used_gb = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    disk_percent_used = Column(Float, nullable=True)
