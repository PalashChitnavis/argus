from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class CpuSnapshot(Base):
    """
    One row per CPU usage collection.
    Collected every 1 minute by the agent.
    """
    __tablename__ = "cpu_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    cpu_percent_used = Column(Float, nullable=True)
