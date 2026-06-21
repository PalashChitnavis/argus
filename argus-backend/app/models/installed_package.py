from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class InstalledPackage(Base):
    __tablename__ = "installed_packages"

    id = Column(Integer, primary_key=True, index=True)
    startup_data_id = Column(Integer, ForeignKey("startup_data.id"), nullable=False, index=True)
    package_name = Column(String, nullable=False, index=True)

    startup_data = relationship("StartupData", back_populates="packages")