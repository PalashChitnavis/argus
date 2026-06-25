from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db import Base

class NewProcess(Base):
    __tablename__ = "new_processes"

    id = Column(Integer, primary_key=True, index=True)
    one_minute_data_id = Column(Integer, ForeignKey("one_minute_data.id"), nullable=False, index=True)

    pid = Column(Integer, nullable=False)
    create_time = Column(Float, nullable=False)
    name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    cmdline = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)

    one_minute_data = relationship("OneMinuteData", back_populates="new_processes")

    __table_args__ = (
        Index("ix_new_processes_pid_create_time", "pid", "create_time"),
    )