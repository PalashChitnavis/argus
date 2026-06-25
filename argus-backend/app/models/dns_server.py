from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class DnsServer(Base):
    __tablename__ = "dns_servers"

    id = Column(Integer, primary_key=True, index=True)
    thirty_minute_data_id = Column(Integer, ForeignKey("thirty_minute_data.id"), nullable=False, index=True)
    address = Column(String, nullable=False)

    thirty_minute_data = relationship("ThirtyMinuteData", back_populates="dns_servers")