from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db import Base


class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    rule_type = Column(String, nullable=False)         # port, ip, domain, etc.
    action = Column(String, nullable=False)            # allow, deny, block, unblock, set, remove
    params = Column(JSON, nullable=False)              # rule-type-specific params dict
    schedule = Column(JSON, nullable=True)             # {start_time, end_time} or null
    enabled = Column(Boolean, default=True, nullable=False)
    applied = Column(Boolean, default=False, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FirewallHistory(Base):
    """Immutable audit log of every rule that was applied or deleted on a node."""
    __tablename__ = "firewall_history"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    rule_id = Column(Integer, nullable=True)           # original rule id (null if rule was deleted)
    event = Column(String, nullable=False)             # "applied" | "deleted" | "failed"
    rule_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    params = Column(JSON, nullable=False)
    schedule = Column(JSON, nullable=True)
    description = Column(String, nullable=True)
    command_id = Column(String, nullable=True)         # which command triggered this
    success = Column(Boolean, nullable=False)
    message = Column(String, nullable=True)            # agent output / error text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
