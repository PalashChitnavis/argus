from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class StartupData(Base):
    __tablename__ = "startup_data"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    # os_info
    distro_name = Column(String, nullable=True)
    distro_version = Column(String, nullable=True)
    distro_codename = Column(String, nullable=True)
    distro_id = Column(String, nullable=True)
    kernel_version = Column(String, nullable=True)
    architecture = Column(String, nullable=True)

    # hardware_info
    cpu_cores_physical = Column(Integer, nullable=True)
    cpu_cores_logical = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_total_gb = Column(Float, nullable=True)

    packages = relationship(
        "InstalledPackage",
        back_populates="startup_data",
        cascade="all, delete-orphan"
    )