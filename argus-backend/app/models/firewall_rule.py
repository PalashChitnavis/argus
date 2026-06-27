from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)

    # Rule type and action — matches the new enforcement schema
    rule_type = Column(String, nullable=False)   # port, ip, ip_port, domain, bandwidth, user_port
    action = Column(String, nullable=False)       # allow, deny, block, unblock, set, remove

    # All rule-type-specific fields stored as JSON (flexible per rule_type)
    params = Column(JSON, nullable=False)

    # Optional schedule: {"start_time": "HH:MM", "end_time": "HH:MM"}
    schedule = Column(JSON, nullable=True)

    # Status flags
    enabled = Column(Boolean, default=True)
    applied = Column(Boolean, default=False)  # True once the end-node confirms it

    # Metadata
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    node = relationship("Node", backref="firewall_rules")