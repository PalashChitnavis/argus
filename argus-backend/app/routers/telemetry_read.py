from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db import get_db
from app.models.node import Node
from app.models.startup_data import StartupData
from app.models.one_minute_data import OneMinuteData
from app.models.five_minute_data import FiveMinuteData
from app.models.thirty_minute_data import ThirtyMinuteData
from app.models.daily_data import DailyData
from app.schemas.telemetry_read import (
    NodeResponse,
    StartupDataResponse,
    OneMinuteDataResponse,
    FiveMinuteDataResponse,
    ThirtyMinuteDataResponse,
    DailyDataResponse
)
from typing import List
from datetime import datetime, timezone, timedelta

router = APIRouter()

# A node is "online" if it polled within the last 30 seconds
# (the agent polls every 10 s, so missing 3 polls = offline)
ONLINE_THRESHOLD = timedelta(seconds=30)


def _node_status(node: Node) -> str:
    if not node.last_seen:
        return "offline"
    age = datetime.now(timezone.utc) - node.last_seen
    return "online" if age <= ONLINE_THRESHOLD else "offline"


# ============ Node Management Endpoints ============

@router.get("/nodes", response_model=List[NodeResponse])
def get_all_nodes(db: Session = Depends(get_db)):
    """Get all registered nodes (frontend endpoint)"""
    nodes = db.query(Node).all()
    return [
        {**node.__dict__, "status": _node_status(node)}
        for node in nodes
    ]


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(node_id: int, db: Session = Depends(get_db)):
    """Get details of a specific node"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {**node.__dict__, "status": _node_status(node)}


@router.get("/nodes/{node_id}/status")
def get_node_status(node_id: int, db: Session = Depends(get_db)):
    """Get node online/offline status and last seen timestamp"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "node_id": node.id,
        "status": _node_status(node),
        "last_seen": node.last_seen,
        "hostname": node.hostname
    }


# ============ Startup Data Endpoints ============

@router.get("/nodes/{node_id}/startup-data", response_model=StartupDataResponse)
def get_latest_startup_data(node_id: int, db: Session = Depends(get_db)):
    """Get latest startup data for a node (for frontend)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    data = db.query(StartupData).filter(
        StartupData.node_id == node_id
    ).order_by(desc(StartupData.received_at)).first()
    if not data:
        raise HTTPException(status_code=404, detail="No startup data found")
    return data


@router.get("/nodes/{node_id}/startup-data/history", response_model=List[StartupDataResponse])
def get_startup_data_history(node_id: int, limit: int = 10, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(StartupData).filter(
        StartupData.node_id == node_id
    ).order_by(desc(StartupData.received_at)).limit(limit).all()


# ============ One Minute Data Endpoints ============

@router.get("/nodes/{node_id}/one-minute-data", response_model=OneMinuteDataResponse)
def get_latest_one_minute_data(node_id: int, db: Session = Depends(get_db)):
    """Get latest 1-minute telemetry for a node (CPU, processes)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    data = db.query(OneMinuteData).filter(
        OneMinuteData.node_id == node_id
    ).order_by(desc(OneMinuteData.received_at)).first()
    if not data:
        raise HTTPException(status_code=404, detail="No one-minute data found")
    return data


@router.get("/nodes/{node_id}/one-minute-data/history", response_model=List[OneMinuteDataResponse])
def get_one_minute_data_history(node_id: int, limit: int = 60, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(OneMinuteData).filter(
        OneMinuteData.node_id == node_id
    ).order_by(desc(OneMinuteData.received_at)).limit(limit).all()


# ============ Five Minute Data Endpoints ============

@router.get("/nodes/{node_id}/five-minute-data", response_model=FiveMinuteDataResponse)
def get_latest_five_minute_data(node_id: int, db: Session = Depends(get_db)):
    """Get latest 5-minute telemetry for a node (disk, RAM, network, logs)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    data = db.query(FiveMinuteData).filter(
        FiveMinuteData.node_id == node_id
    ).order_by(desc(FiveMinuteData.received_at)).first()
    if not data:
        raise HTTPException(status_code=404, detail="No five-minute data found")
    return data


@router.get("/nodes/{node_id}/five-minute-data/history", response_model=List[FiveMinuteDataResponse])
def get_five_minute_data_history(node_id: int, limit: int = 288, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(FiveMinuteData).filter(
        FiveMinuteData.node_id == node_id
    ).order_by(desc(FiveMinuteData.received_at)).limit(limit).all()


# ============ Thirty Minute Data Endpoints ============

@router.get("/nodes/{node_id}/thirty-minute-data", response_model=ThirtyMinuteDataResponse)
def get_latest_thirty_minute_data(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    data = db.query(ThirtyMinuteData).filter(
        ThirtyMinuteData.node_id == node_id
    ).order_by(desc(ThirtyMinuteData.received_at)).first()
    if not data:
        raise HTTPException(status_code=404, detail="No thirty-minute data found")
    return data


@router.get("/nodes/{node_id}/thirty-minute-data/history", response_model=List[ThirtyMinuteDataResponse])
def get_thirty_minute_data_history(node_id: int, limit: int = 48, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(ThirtyMinuteData).filter(
        ThirtyMinuteData.node_id == node_id
    ).order_by(desc(ThirtyMinuteData.received_at)).limit(limit).all()


# ============ Daily Data Endpoints ============

@router.get("/nodes/{node_id}/daily-data", response_model=DailyDataResponse)
def get_latest_daily_data(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    data = db.query(DailyData).filter(
        DailyData.node_id == node_id
    ).order_by(desc(DailyData.received_at)).first()
    if not data:
        raise HTTPException(status_code=404, detail="No daily data found")
    return data


@router.get("/nodes/{node_id}/daily-data/history", response_model=List[DailyDataResponse])
def get_daily_data_history(node_id: int, limit: int = 30, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db.query(DailyData).filter(
        DailyData.node_id == node_id
    ).order_by(desc(DailyData.received_at)).limit(limit).all()


# ============ Combined Dashboard Endpoint ============

@router.get("/nodes/{node_id}/dashboard")
def get_node_dashboard(node_id: int, db: Session = Depends(get_db)):
    """Get all latest telemetry data for a node dashboard (for frontend)"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    startup_data   = db.query(StartupData).filter(StartupData.node_id == node_id).order_by(desc(StartupData.received_at)).first()
    one_minute     = db.query(OneMinuteData).filter(OneMinuteData.node_id == node_id).order_by(desc(OneMinuteData.received_at)).first()
    five_minute    = db.query(FiveMinuteData).filter(FiveMinuteData.node_id == node_id).order_by(desc(FiveMinuteData.received_at)).first()
    thirty_minute  = db.query(ThirtyMinuteData).filter(ThirtyMinuteData.node_id == node_id).order_by(desc(ThirtyMinuteData.received_at)).first()
    daily_data     = db.query(DailyData).filter(DailyData.node_id == node_id).order_by(desc(DailyData.received_at)).first()

    return {
        "node": {
            "id": node.id,
            "hostname": node.hostname,
            "machine_id": node.machine_id,
            "status": _node_status(node),
            "last_seen": node.last_seen
        },
        "startup_data": startup_data,
        "one_minute_data": one_minute,
        "five_minute_data": five_minute,
        "thirty_minute_data": thirty_minute,
        "daily_data": daily_data
    }