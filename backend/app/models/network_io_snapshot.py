from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class NetworkIoSnapshot(Base):
    """
    One row per network I/O collection.
    Collected every 5 minutes by the agent.
    """
    __tablename__ = "network_io_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    bytes_sent_mb = Column(Float, nullable=True)
    bytes_recv_mb = Column(Float, nullable=True)
