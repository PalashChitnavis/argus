from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db import get_db
from app.core.auth import get_current_node
from app.models.node import Node
from app.models.firewall_rule import FirewallRule, FirewallHistory
from app.models.command import Command
from app.schemas.firewall import (
    FirewallRuleCreate,
    FirewallRuleUpdate,
    FirewallRuleResponse,
)
from app.schemas.firewall_commands import (
    FirewallStatusResponse,
    ScheduleInfo,
)
from typing import List, Any, Dict, Optional

from pydantic import BaseModel
import uuid

router = APIRouter()


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_enforce_command(db: Session, node_id: int, rule: FirewallRule) -> Command:
    """Queue an enforce command for a rule; return the Command object (not yet committed)."""
    payload: Dict[str, Any] = {
        "rule_type": rule.rule_type,
        "action": rule.action,
        "params": rule.params,
        "rule_id": rule.id,        # carried back in result so we can update applied flag
    }
    if rule.schedule:
        payload["schedule"] = rule.schedule
    cmd = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="enforce",
        payload=payload,
    )
    db.add(cmd)
    return cmd


def _make_delete_command(db: Session, node_id: int, rule: FirewallRule) -> Command:
    """Queue a delete_rule command; return the Command object (not yet committed)."""
    payload: Dict[str, Any] = {
        "rule_type": rule.rule_type,
        "action": rule.action,
        "params": rule.params,
        "rule_id": rule.id,
    }
    if rule.schedule:
        payload["schedule"] = rule.schedule
    cmd = Command(
        command_id=str(uuid.uuid4()),
        node_id=node_id,
        command_type="delete_rule",
        payload=payload,
    )
    db.add(cmd)
    return cmd


def _add_history(
    db: Session,
    node_id: int,
    rule: FirewallRule,
    event: str,
    success: bool,
    message: str = None,
    command_id: str = None,
):
    entry = FirewallHistory(
        node_id=node_id,
        rule_id=rule.id,
        event=event,
        rule_type=rule.rule_type,
        action=rule.action,
        params=rule.params,
        schedule=rule.schedule,
        description=rule.description,
        command_id=command_id,
        success=success,
        message=message,
    )
    db.add(entry)


# ─── Frontend CRUD ────────────────────────────────────────────────────────────

@router.post("/nodes/{node_id}/firewall-rules", response_model=FirewallRuleResponse, status_code=201)
def create_firewall_rule(node_id: int, rule: FirewallRuleCreate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    valid_rule_types = ["port", "ip", "ip_port", "domain", "bandwidth", "user_port"]
    if rule.rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of {valid_rule_types}")

    db_rule = FirewallRule(
        node_id=node_id,
        rule_type=rule.rule_type,
        action=rule.action,
        params=rule.params,
        schedule=rule.schedule.dict() if rule.schedule else None,
        enabled=rule.enabled,
        description=rule.description,
        applied=False,
    )
    db.add(db_rule)
    db.flush()  # get db_rule.id

    if rule.enabled:
        _make_enforce_command(db, node_id, db_rule)

    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/nodes/{node_id}/firewall-rules", response_model=List[FirewallRuleResponse])
def get_firewall_rules(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(FirewallRule).filter(
        FirewallRule.node_id == node_id
    ).order_by(desc(FirewallRule.created_at)).all()


@router.get("/nodes/{node_id}/firewall-rules/{rule_id}", response_model=FirewallRuleResponse)
def get_firewall_rule(node_id: int, rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id, FirewallRule.node_id == node_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    return rule


@router.put("/nodes/{node_id}/firewall-rules/{rule_id}", response_model=FirewallRuleResponse)
def update_firewall_rule(
    node_id: int, rule_id: int, rule_update: FirewallRuleUpdate, db: Session = Depends(get_db)
):
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id, FirewallRule.node_id == node_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")

    old_enabled = rule.enabled
    update_data = rule_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "schedule" and value is not None:
            setattr(rule, key, value.dict() if isinstance(value, ScheduleInfo) else value)
        else:
            setattr(rule, key, value)

    rule.applied = False  # needs re-enforcement

    if not old_enabled and rule.enabled:
        _make_enforce_command(db, node_id, rule)
    elif old_enabled and not rule.enabled and rule.applied:
        _make_delete_command(db, node_id, rule)
    elif rule.enabled:
        # Rule was already enabled — re-enforce with updated params
        _make_enforce_command(db, node_id, rule)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/nodes/{node_id}/firewall-rules/{rule_id}", status_code=204)
def delete_firewall_rule(node_id: int, rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == rule_id, FirewallRule.node_id == node_id
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")

    # If the rule was ever applied, send a delete command so the node undoes it.
    # We record history here (optimistically) — the command result endpoint will
    # update the history row once the agent confirms.
    if rule.enabled:
        cmd = _make_delete_command(db, node_id, rule)
        db.flush()
        _add_history(
            db, node_id, rule,
            event="deleted",
            success=True,
            message="Delete command queued",
            command_id=cmd.command_id,
        )

    db.delete(rule)
    db.commit()


# ─── History endpoint (frontend) ──────────────────────────────────────────────

@router.get("/nodes/{node_id}/firewall-history")
def get_firewall_history(node_id: int, limit: int = 100, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    entries = db.query(FirewallHistory).filter(
        FirewallHistory.node_id == node_id
    ).order_by(desc(FirewallHistory.created_at)).limit(limit).all()

    return [
        {
            "id": e.id,
            "rule_id": e.rule_id,
            "event": e.event,
            "rule_type": e.rule_type,
            "action": e.action,
            "params": e.params,
            "schedule": e.schedule,
            "description": e.description,
            "command_id": e.command_id,
            "success": e.success,
            "message": e.message,
            "created_at": e.created_at,
        }
        for e in entries
    ]


# ─── Linux End Node endpoints ────────────────────────────────────────────────

class FirewallResultRequest(BaseModel):
    rule_id: int
    command_id: str
    event: str          # "applied" | "deleted"
    success: bool
    message: Optional[str] = None


@router.post("/nodes/{node_id}/firewall-rules/apply-status", status_code=200)
def post_firewall_rule_status(
    node_id: int,
    request: FirewallResultRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Agent calls this after executing an enforce or delete_rule command."""
    if node.id != node_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Update the FirewallRule if it still exists (may have been deleted from frontend already)
    rule = db.query(FirewallRule).filter(
        FirewallRule.id == request.rule_id,
        FirewallRule.node_id == node_id,
    ).first()

    if rule and request.event == "applied":
        if request.success:
            rule.applied = True
        else:
            rule.applied = False

    # Always write a history entry
    if rule:
        _add_history(
            db, node_id, rule,
            event=request.event,
            success=request.success,
            message=request.message,
            command_id=request.command_id,
        )
    else:
        # Rule was deleted from DB — still record history with what we know
        # Look up the history entry created during delete
        existing = db.query(FirewallHistory).filter(
            FirewallHistory.command_id == request.command_id,
            FirewallHistory.node_id == node_id,
        ).first()
        if existing:
            existing.success = request.success
            existing.message = request.message

    db.commit()
    return {"status": "ok", "rule_id": request.rule_id}


# ─── Firewall status ──────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/firewall-status")
def get_firewall_status(node_id: int, db: Session = Depends(get_db)) -> FirewallStatusResponse:
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    all_rules = db.query(FirewallRule).filter(FirewallRule.node_id == node_id).all()
    total = len(all_rules)
    enabled = sum(1 for r in all_rules if r.enabled)
    applied = sum(1 for r in all_rules if r.applied)
    pending = sum(1 for r in all_rules if r.enabled and not r.applied)
    rules_by_type: Dict[str, int] = {}
    for r in all_rules:
        rules_by_type[r.rule_type] = rules_by_type.get(r.rule_type, 0) + 1

    return FirewallStatusResponse(
        node_id=node_id,
        total_rules=total,
        enabled_rules=enabled,
        applied_rules=applied,
        pending_rules=pending,
        rules_by_type=rules_by_type,
    )
