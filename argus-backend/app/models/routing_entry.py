from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class RoutingEntry(Base):
    __tablename__ = "routing_table"

    id = Column(Integer, primary_key=True, index=True)
    thirty_minute_data_id = Column(Integer, ForeignKey("thirty_minute_data.id"), nullable=False, index=True)
    route = Column(Text, nullable=False)

    thirty_minute_data = relationship("ThirtyMinuteData", back_populates="routing_table")