from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class RoutingEntry(Base):
    """
    Routing table entries from the node.
    Rows from one collection share the same batch_id.
    Collected every 30 minutes by the agent.
    """
    __tablename__ = "routing_entries"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    route = Column(Text, nullable=False)
