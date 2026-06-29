from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db import get_db
from app.core.auth import get_current_node
from app.models.node import Node
from app.models.firewall_rule import FirewallRule
from app.models.command import Command
from app.schemas.firewall import (
    FirewallRuleCreate,
    FirewallRuleUpdate,
    FirewallRuleResponse,
    FirewallRuleUpdateRequest
)
from app.schemas.firewall_commands import (
    FirewallStatusResponse,
    ScheduleInfo
)
from typing import List
from datetime import datetime, timezone
import uuid

router = APIRouter()


# ============ Frontend Endpoints - CRUD Operations ============

@router.post("/nodes/{node_id}/firewall-rules", response_model=FirewallRuleResponse, status_code=201)
def create_firewall_rule(
    node_id: int,
    rule: FirewallRuleCreate,
    db: Session = Depends(get_db)
):
    """Create a new firewall rule for a node (Frontend Admin)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Validate rule_type
    valid_rule_types = ["port", "ip", "ip_port", "domain", "bandwidth", "user_port"]
    if rule.rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of {valid_rule_types}")
    
    # Create the firewall rule
    db_rule = FirewallRule(
        node_id=node_id,
        rule_type=rule.rule_type,
        action=rule.action,
        params=rule.params,
        schedule=rule.schedule.dict() if rule.schedule else None,
        enabled=rule.enabled,
        description=rule.description
    )
    db.add(db_rule)
    db.flush()
    
    # Create an enforce command for this rule
    if rule.enabled:
        enforce_payload = {
            "rule_type": rule.rule_type,
            "action": rule.action,
            "params": rule.params,
        }
        if rule.schedule:
            enforce_payload["schedule"] = rule.schedule.dict()
        
        command = Command(
            command_id=str(uuid.uuid4()),
            node_id=node_id,
            command_type="enforce",
            payload=enforce_payload
        )
        db.add(command)
    
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/nodes/{node_id}/firewall-rules", response_model=List[FirewallRuleResponse])
def get_firewall_rules(
    node_id: int,
    db: Session = Depends(get_db)
):
    """Get all firewall rules for a node (Frontend)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id
    ).order_by(desc(FirewallRule.created_at)).all()
    
    return rules


@router.get("/nodes/{node_id}/firewall-rules/{rule_id}", response_model=FirewallRuleResponse)
def get_firewall_rule(
    node_id: int,
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific firewall rule (Frontend)"""
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id,
        FirewallRule.node_id == node_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    
    return rule


@router.put("/nodes/{node_id}/firewall-rules/{rule_id}", response_model=FirewallRuleResponse)
def update_firewall_rule(
    node_id: int,
    rule_id: int,
    rule_update: FirewallRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update a firewall rule (Frontend Admin)"""
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id,
        FirewallRule.node_id == node_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    
    # Update fields that were provided
    update_data = rule_update.dict(exclude_unset=True)
    
    old_enabled = rule.enabled
    for key, value in update_data.items():
        if key == "schedule" and value is not None:
            setattr(rule, key, value.dict() if isinstance(value, ScheduleInfo) else value)
        else:
            setattr(rule, key, value)
    
    # Mark as not applied when rule is updated (needs to be re-applied to node)
    rule.applied = False
    
    # Create a new enforce command if the rule is being enabled
    if not old_enabled and rule.enabled:
        enforce_payload = {
            "rule_type": rule.rule_type,
            "action": rule.action,
            "params": rule.params,
        }
        if rule.schedule:
            enforce_payload["schedule"] = rule.schedule
        
        command = Command(
            command_id=str(uuid.uuid4()),
            node_id=node_id,
            command_type="enforce",
            payload=enforce_payload
        )
        db.add(command)
    # Or create a delete command if the rule is being disabled
    elif old_enabled and not rule.enabled:
        delete_payload = {
            "rule_type": rule.rule_type,
            "rule_id": rule.id
        }
        command = Command(
            command_id=str(uuid.uuid4()),
            node_id=node_id,
            command_type="delete_rule",
            payload=delete_payload
        )
        db.add(command)
    
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/nodes/{node_id}/firewall-rules/{rule_id}", status_code=204)
def delete_firewall_rule(
    node_id: int,
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Delete a firewall rule (Frontend Admin)"""
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id,
        FirewallRule.node_id == node_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    
    # Create a delete command if rule was applied
    if rule.applied:
        delete_payload = {
            "rule_type": rule.rule_type,
            "rule_id": rule.id
        }
        command = Command(
            command_id=str(uuid.uuid4()),
            node_id=node_id,
            command_type="delete_rule",
            payload=delete_payload
        )
        db.add(command)
    
    db.delete(rule)
    db.commit()


# ============ Linux End Node Endpoints ============

@router.get("/nodes/{node_id}/firewall-rules/pending")
def get_pending_firewall_rules(
    node_id: int,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    """Get firewall rules that need to be applied to the node (Linux End Node)"""
    if node.id != node_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Get all enabled rules that haven't been applied yet
    pending_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id,
        FirewallRule.enabled == True,
        FirewallRule.applied == False
    ).all()
    
    return {
        "node_id": node_id,
        "pending_rules": [
            {
                "id": rule.id,
                "rule_type": rule.rule_type,
                "action": rule.action,
                "params": rule.params,
                "schedule": rule.schedule,
                "description": rule.description
            }
            for rule in pending_rules
        ]
    }


@router.post("/nodes/{node_id}/firewall-rules/apply-status", status_code=200)
def post_firewall_rule_status(
    node_id: int,
    request: FirewallRuleUpdateRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    """Report firewall rule application status from Linux End Node"""
    if node.id != node_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == request.rule_id,
        FirewallRule.node_id == node_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    
    # Update the applied status
    if request.status == "success":
        rule.applied = True
    else:
        rule.applied = False
    
    db.commit()
    
    return {
        "status": "updated",
        "rule_id": rule.id,
        "applied": rule.applied
    }


@router.get("/nodes/{node_id}/firewall-status")
def get_firewall_status(
    node_id: int,
    db: Session = Depends(get_db)
) -> FirewallStatusResponse:
    """Get overall firewall status for a node"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    total_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id
    ).count()
    
    applied_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id,
        FirewallRule.applied == True
    ).count()
    
    enabled_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id,
        FirewallRule.enabled == True
    ).count()
    
    pending_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id,
        FirewallRule.enabled == True,
        FirewallRule.applied == False
    ).count()
    
    # Get count by rule type
    rules_by_type = {}
    all_rules = db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id
    ).all()
    for rule in all_rules:
        rules_by_type[rule.rule_type] = rules_by_type.get(rule.rule_type, 0) + 1
    
    return FirewallStatusResponse(
        node_id=node_id,
        total_rules=total_rules,
        enabled_rules=enabled_rules,
        applied_rules=applied_rules,
        pending_rules=pending_rules,
        rules_by_type=rules_by_type
    )
