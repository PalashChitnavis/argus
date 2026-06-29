from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class AuthEvent(Base):
    """
    Auth log lines (SSH logins, sudo, su, etc.) from the agent.
    Rows from one collection share the same batch_id.
    Collected every 5 minutes by the agent.
    """
    __tablename__ = "auth_events"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    log_line = Column(Text, nullable=False)
