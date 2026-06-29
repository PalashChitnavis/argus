from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class ThirtyMinuteData(Base):
    __tablename__ = "thirty_minute_data"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # firewall_status
    firewall_tool = Column(String, nullable=True)
    firewall_active = Column(Boolean, nullable=True)

    # disk_encryption
    disk_encrypted = Column(Boolean, nullable=True)

    # ssh_config
    root_login_permitted = Column(Boolean, nullable=True)
    password_auth_permitted = Column(Boolean, nullable=True)

    # mac_status
    mac_tool = Column(String, nullable=True)
    mac_enabled = Column(Boolean, nullable=True)

    interfaces = relationship(
        "NetworkInterface",
        back_populates="thirty_minute_data",
        cascade="all, delete-orphan"
    )
    dns_servers = relationship(
        "DnsServer",
        back_populates="thirty_minute_data",
        cascade="all, delete-orphan"
    )
    routing_table = relationship(
        "RoutingEntry",
        back_populates="thirty_minute_data",
        cascade="all, delete-orphan"
    )