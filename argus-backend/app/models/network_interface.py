from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class NetworkInterface(Base):
    __tablename__ = "network_interfaces"

    id = Column(Integer, primary_key=True, index=True)
    thirty_minute_data_id = Column(Integer, ForeignKey("thirty_minute_data.id"), nullable=False, index=True)

    interface_name = Column(String, nullable=True)
    ipv4 = Column(String, nullable=True)
    ipv6 = Column(String, nullable=True)
    mac_address = Column(String, nullable=True)

    thirty_minute_data = relationship("ThirtyMinuteData", back_populates="interfaces")