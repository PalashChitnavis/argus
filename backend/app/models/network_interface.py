from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class NetworkInterface(Base):
    """
    One row per network interface per collection batch.
    Rows from one collection share the same batch_id.
    Collected every 30 minutes by the agent.
    """
    __tablename__ = "network_interfaces"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    interface_name = Column(String, nullable=True)
    ipv4 = Column(String, nullable=True)
    ipv6 = Column(String, nullable=True)
    mac_address = Column(String, nullable=True)
