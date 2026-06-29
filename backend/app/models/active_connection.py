from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class ActiveConnection(Base):
    """
    Each row is one network connection captured in a single collection batch.
    All rows from one collection share the same batch_id (UUID).
    Collected every 5 minutes by the agent.
    """
    __tablename__ = "active_connections"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)   # groups one collection cycle
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    local_ip = Column(String, nullable=True)
    local_port = Column(Integer, nullable=True)
    remote_ip = Column(String, nullable=True)
    remote_port = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    pid = Column(Integer, nullable=True)
    process_name = Column(String, nullable=True)
