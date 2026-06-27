from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, unique=True, nullable=False, index=True)  # UUID
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    
    # Command type: refresh, enforce, delete_rule, get_rules
    command_type = Column(String, nullable=False, index=True)
    
    # Command payload - structure depends on command_type
    payload = Column(JSON, nullable=False)
    
    # Status
    executed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    node = relationship("Node", backref="commands")
    result = relationship("CommandResult", back_populates="command", uselist=False, cascade="all, delete-orphan")


class CommandResult(Base):
    __tablename__ = "command_results"

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String, ForeignKey("commands.command_id"), nullable=False, index=True)
    
    # Execution status
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    
    # Result data - structure depends on command type
    data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    command = relationship("Command", back_populates="result")
