from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class InstalledPackage(Base):
    """
    Installed packages on the node.
    Rows from one collection share the same batch_id.
    Collected once daily by the agent.
    """
    __tablename__ = "installed_packages"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    package_name = Column(String, nullable=False, index=True)
