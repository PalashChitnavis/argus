from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class RecentLog(Base):
    __tablename__ = "recent_logs"

    id = Column(Integer, primary_key=True, index=True)
    five_minute_data_id = Column(Integer, ForeignKey("five_minute_data.id"), nullable=False, index=True)
    log_line = Column(Text, nullable=False)

    five_minute_data = relationship("FiveMinuteData", back_populates="recent_logs")