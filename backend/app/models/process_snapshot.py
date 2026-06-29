from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.db import Base

class ProcessSnapshot(Base):
    """
    One row per process per collection cycle.
    The agent diffs against the previous snapshot and only sends NEW processes.
    Collected every 1 minute.
    """
    __tablename__ = "process_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    pid = Column(Integer, nullable=False)
    create_time = Column(Float, nullable=False)
    name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    cmdline = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_process_snapshots_pid_create_time", "pid", "create_time"),
    )
