from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class DnsServer(Base):
    """
    DNS server addresses configured on the node.
    Rows from one collection share the same batch_id.
    Collected every 30 minutes by the agent.
    """
    __tablename__ = "dns_servers"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    address = Column(String, nullable=False)
