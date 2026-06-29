from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    rule_number = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    protocol = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    source = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    direction = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
