from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class FiveMinuteData(Base):
    __tablename__ = "five_minute_data"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # disk_usage
    disk_used_gb = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    disk_percent_used = Column(Float, nullable=True)

    # ram_usage
    ram_used_gb = Column(Float, nullable=True)
    ram_available_gb = Column(Float, nullable=True)
    ram_percent_used = Column(Float, nullable=True)

    # network_io
    bytes_sent_mb = Column(Float, nullable=True)
    bytes_recv_mb = Column(Float, nullable=True)

    connections = relationship(
        "NetworkConnection",
        back_populates="five_minute_data",
        cascade="all, delete-orphan"
    )
    recent_logs = relationship(
        "RecentLog",
        back_populates="five_minute_data",
        cascade="all, delete-orphan"
    )
    auth_events = relationship(
        "AuthEvent",
        back_populates="five_minute_data",
        cascade="all, delete-orphan"
    )