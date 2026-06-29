from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class SecurityStatus(Base):
    """
    Point-in-time snapshot of the node's security configuration:
    firewall, disk encryption, SSH settings, MAC enforcement.
    Collected every 30 minutes by the agent.
    """
    __tablename__ = "security_status"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # Firewall
    firewall_tool = Column(String, nullable=True)
    firewall_active = Column(Boolean, nullable=True)

    # Disk encryption
    disk_encrypted = Column(Boolean, nullable=True)

    # SSH config
    root_login_permitted = Column(Boolean, nullable=True)
    password_auth_permitted = Column(Boolean, nullable=True)

    # MAC (AppArmor / SELinux)
    mac_tool = Column(String, nullable=True)
    mac_enabled = Column(Boolean, nullable=True)
