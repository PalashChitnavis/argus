"""
Anomaly detection endpoints, admin/frontend-facing (no node auth, same as
nodes_read.py and firewall.py — these are called by the dashboard, not the
agent).

POST /nodes/{node_id}/anomaly-scan   — fit IsolationForest on recent windows, persist + return flags
GET  /nodes/{node_id}/anomalies      — list stored anomaly results
PATCH /nodes/{node_id}/anomalies/{anomaly_id}/dismiss — mark one as reviewed
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.db import get_db
from app.models.node import Node
from app.models.anomaly_result import AnomalyResult
from app.schemas.anomaly import AnomalyScanResponse, AnomalyResultResponse
from app.services.anomaly_detection import run_anomaly_scan

router = APIRouter()


def _get_node_or_404(node_id: int, db: Session) -> Node:
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/nodes/{node_id}/anomaly-scan", response_model=AnomalyScanResponse)
def scan_for_anomalies(node_id: int, hours: int = 6, db: Session = Depends(get_db)):
    """
    Refits IsolationForest on this node's last `hours` of telemetry
    (bucketed into 5-min windows) and upserts any flagged windows into
    anomaly_results, keyed on (node_id, window_start) so re-scanning the
    same window doesn't duplicate it.
    """
    _get_node_or_404(node_id, db)

    result = run_anomaly_scan(db, node_id, hours)

    saved: List[AnomalyResult] = []
    for f in result["flagged"]:
        existing = (
            db.query(AnomalyResult)
            .filter(AnomalyResult.node_id == node_id, AnomalyResult.window_start == f["window_start"])
            .first()
        )
        if existing:
            existing.window_end = f["window_end"]
            existing.anomaly_score = f["anomaly_score"]
            existing.features = f["features"]
            existing.contributing_features = f["contributing_features"]
            saved.append(existing)
        else:
            row = AnomalyResult(
                node_id=node_id,
                window_start=f["window_start"],
                window_end=f["window_end"],
                anomaly_score=f["anomaly_score"],
                features=f["features"],
                contributing_features=f["contributing_features"],
            )
            db.add(row)
            saved.append(row)

    db.commit()
    for row in saved:
        db.refresh(row)

    saved.sort(key=lambda r: r.window_start, reverse=True)

    return AnomalyScanResponse(
        node_id=node_id,
        scan_range_start=result["scan_start"],
        scan_range_end=result["scan_end"],
        windows_scanned=result["window_count"],
        anomalies_found=len(saved),
        anomalies=[AnomalyResultResponse.model_validate(r) for r in saved],
        message=result["message"],
    )


@router.get("/nodes/{node_id}/anomalies", response_model=List[AnomalyResultResponse])
def list_anomalies(node_id: int, include_dismissed: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    query = db.query(AnomalyResult).filter(AnomalyResult.node_id == node_id)
    if not include_dismissed:
        query = query.filter(AnomalyResult.dismissed == False)  # noqa: E712
    rows = query.order_by(desc(AnomalyResult.window_start)).limit(limit).all()
    return rows


@router.patch("/nodes/{node_id}/anomalies/{anomaly_id}/dismiss", response_model=AnomalyResultResponse)
def dismiss_anomaly(node_id: int, anomaly_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.id == anomaly_id, AnomalyResult.node_id == node_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    row.dismissed = True
    row.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
