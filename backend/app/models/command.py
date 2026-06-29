from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, unique=True, nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    command_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    executed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

    result = relationship("CommandResult", back_populates="command", uselist=False)


class CommandResult(Base):
    __tablename__ = "command_results"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, ForeignKey("commands.command_id"), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    command = relationship("Command", back_populates="result")
