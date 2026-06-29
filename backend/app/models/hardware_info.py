from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class HardwareInfo(Base):
    """
    Hardware specs of the node.
    Collected on startup and once daily.
    """
    __tablename__ = "hardware_info"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    cpu_cores_physical = Column(Integer, nullable=True)
    cpu_cores_logical = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_total_gb = Column(Float, nullable=True)
