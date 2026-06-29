from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db import Base

class FirewallRule(Base):
    """
    A rule the admin wants enforced on a node.

    Shape matches app/schemas/firewall_commands.py (FirewallRuleBase) and
    what app/routers/firewall.py reads/writes: rule_type + action + a
    flexible params blob (different fields depending on rule_type), an
    optional time-based schedule, and enabled/applied flags tracking
    desired-vs-actual state.
    """
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)

    rule_type = Column(String, nullable=False)   # port | ip | ip_port | domain | bandwidth | user_port
    action = Column(String, nullable=False)       # allow | deny | block | unblock | set | remove
    params = Column(JSON, nullable=False)         # shape depends on rule_type — see API_DOCUMENTATION.md
    schedule = Column(JSON, nullable=True)        # optional {"start_time": "HH:MM", "end_time": "HH:MM"}

    enabled = Column(Boolean, default=True, nullable=False)   # admin's desired state
    applied = Column(Boolean, default=False, nullable=False)  # whether the node has actually applied it
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
