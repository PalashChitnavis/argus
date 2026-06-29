from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class NetworkConnection(Base):
    __tablename__ = "network_connections"

    id = Column(Integer, primary_key=True, index=True)
    five_minute_data_id = Column(Integer, ForeignKey("five_minute_data.id"), nullable=False, index=True)

    local_ip = Column(String, nullable=True)
    local_port = Column(Integer, nullable=True)
    remote_ip = Column(String, nullable=True)
    remote_port = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    pid = Column(Integer, nullable=True)
    process_name = Column(String, nullable=True)

    five_minute_data = relationship("FiveMinuteData", back_populates="connections")