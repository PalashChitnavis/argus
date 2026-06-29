from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class DailyInstalledPackage(Base):
    __tablename__ = "daily_installed_packages"

    id = Column(Integer, primary_key=True, index=True)
    daily_data_id = Column(Integer, ForeignKey("daily_data.id"), nullable=False, index=True)
    package_name = Column(String, nullable=False, index=True)

    daily_data = relationship("DailyData", back_populates="packages")