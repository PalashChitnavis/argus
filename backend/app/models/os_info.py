from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class OsInfo(Base):
    """
    OS identity information from the node.
    Collected on startup and once daily.
    """
    __tablename__ = "os_info"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    distro_name = Column(String, nullable=True)
    distro_version = Column(String, nullable=True)
    distro_codename = Column(String, nullable=True)
    distro_id = Column(String, nullable=True)
    kernel_version = Column(String, nullable=True)
    architecture = Column(String, nullable=True)
