from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db import get_db
from app.core.auth import get_current_node
from app.models.node import Node
from app.models.command import Command, CommandResult
from app.schemas.firewall_commands import (
    CommandOut,
    PendingCommandsResponse,
    CommandResultRequest,
    RefreshCommandPayload,
    EnforceCommandPayload,
    DeleteRuleCommandPayload
)
from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any

router = APIRouter()


# ============ Frontend Admin Endpoints - Create Commands ============

@router.post("/nodes/{node_id}/commands/refresh", status_code=201)
def create_refresh_command(
    node_id: int,
    payload: RefreshCommandPayload,
    db: Session = Depends(get_db)
):
    """
    Create a refresh command for a node (Frontend Admin)
    Refresh pulls fresh data for a specific collector
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    command = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="refresh",
        payload=payload.dict()
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    
    return {
        "command_id": command.command_id,
        "status": "created",
        "type": "refresh"
    }


@router.post("/nodes/{node_id}/commands/enforce", status_code=201)
def create_enforce_command(
    node_id: int,
    payload: EnforceCommandPayload,
    db: Session = Depends(get_db)
):
    """
    Create an enforce command (apply a firewall/security rule)
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    command = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="enforce",
        payload=payload.dict()
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    
    return {
        "command_id": command.command_id,
        "status": "created",
        "type": "enforce",
        "rule_type": payload.rule_type
    }


@router.post("/nodes/{node_id}/commands/delete-rule", status_code=201)
def create_delete_rule_command(
    node_id: int,
    payload: DeleteRuleCommandPayload,
    db: Session = Depends(get_db)
):
    """
    Create a delete rule command
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    command = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="delete_rule",
        payload=payload.dict()
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    
    return {
        "command_id": command.command_id,
        "status": "created",
        "type": "delete_rule"
    }


@router.post("/nodes/{node_id}/commands/get-rules", status_code=201)
def create_get_rules_command(
    node_id: int,
    db: Session = Depends(get_db)
):
    """
    Create a get_rules command (fetch current enforcement state from node)
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    command = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="get_rules",
        payload={}
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    
    return {
        "command_id": command.command_id,
        "status": "created",
        "type": "get_rules"
    }


# ============ Linux End Node Endpoints ============

@router.get("/nodes/{node_id}/commands/pending", response_model=PendingCommandsResponse)
def get_pending_commands(
    node_id: int,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    """
    Get pending commands for a node (called by Linux End Node every 10 seconds)
    Also serves as heartbeat for online/offline tracking
    """
    if node.id != node_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Update last_seen for online/offline tracking
    node.last_seen = datetime.now(timezone.utc)
    db.commit()

    # Get all unexecuted commands for this node, ordered by creation time
    pending_commands = db.query(Command).filter(
        Command.node_id == node_id,
        Command.executed == False
    ).order_by(Command.created_at).all()
    
    commands = [
        CommandOut(
            command_id=cmd.command_id,
            type=cmd.command_type,
            payload=cmd.payload
        )
        for cmd in pending_commands
    ]
    
    return PendingCommandsResponse(commands=commands)


@router.post("/nodes/{node_id}/commands/{command_id}/result", status_code=200)
def post_command_result(
    node_id: int,
    command_id: str,
    request: CommandResultRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    """
    Report command execution result from Linux End Node
    """
    if node.id != node_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Find the command
    command = db.query(Command).filter(
        Command.command_id == command_id,
        Command.node_id == node_id
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    # Mark command as executed
    command.executed = True
    command.executed_at = datetime.now(timezone.utc)
    db.commit()
    
    # Store the command result
    result = CommandResult(
        command_id=command_id,
        success=request.success,
        error_message=request.error_message,
        data=request.data
    )
    db.add(result)
    db.commit()
    
    return {"status": "ok", "command_id": command_id}


# ============ Frontend Query Endpoints ============

@router.get("/nodes/{node_id}/commands", response_model=List[Dict[str, Any]])
def get_node_commands(
    node_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get command history for a node
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    commands = db.query(Command).filter(
        Command.node_id == node_id
    ).order_by(desc(Command.created_at)).limit(limit).all()
    
    result = []
    for cmd in commands:
        cmd_dict = {
            "command_id": cmd.command_id,
            "type": cmd.command_type,
            "payload": cmd.payload,
            "executed": cmd.executed,
            "created_at": cmd.created_at,
            "executed_at": cmd.executed_at,
            "result": None
        }
        
        if cmd.result:
            cmd_dict["result"] = {
                "success": cmd.result.success,
                "error_message": cmd.result.error_message,
                "data": cmd.result.data,
                "created_at": cmd.result.created_at
            }
        
        result.append(cmd_dict)
    
    return result


@router.get("/nodes/{node_id}/commands/{command_id}", response_model=Dict[str, Any])
def get_command(
    node_id: int,
    command_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific command and its result
    """
    command = db.query(Command).filter(
        Command.command_id == command_id,
        Command.node_id == node_id
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    result_data = None
    if command.result:
        result_data = {
            "success": command.result.success,
            "error_message": command.result.error_message,
            "data": command.result.data,
            "created_at": command.result.created_at
        }
    
    return {
        "command_id": command.command_id,
        "type": command.command_type,
        "payload": command.payload,
        "executed": command.executed,
        "created_at": command.created_at,
        "executed_at": command.executed_at,
        "result": result_data
    }


@router.delete("/nodes/{node_id}/commands/{command_id}", status_code=204)
def delete_command(
    node_id: int,
    command_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a command (only works if not yet executed)
    """
    command = db.query(Command).filter(
        Command.command_id == command_id,
        Command.node_id == node_id
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    if command.executed:
        raise HTTPException(status_code=400, detail="Cannot delete executed command")
    
    db.delete(command)
    db.commit()
