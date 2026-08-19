"""
Read-side API for the frontend: node list/detail/status, a combined
"overview" (dashboard) endpoint, and history endpoints for every telemetry
type the agent collects.

This replaces the old telemetry_read.py, which queried tables
(StartupData, OneMinuteData, FiveMinuteData, ThirtyMinuteData, DailyData)
that no longer exist after the schema redesign. Every query below targets
the current per-collector snapshot tables instead (see app/models/).

None of these endpoints require node auth (get_current_node) — they're
called by the admin frontend, not the Linux agent, same as the existing
firewall.py admin endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone, timedelta
from typing import List

from app.db import get_db
from app.models.node import Node
from app.models.os_info import OsInfo
from app.models.hardware_info import HardwareInfo
from app.models.installed_package import InstalledPackage
from app.models.cpu_snapshot import CpuSnapshot
from app.models.process_snapshot import ProcessSnapshot
from app.models.disk_snapshot import DiskSnapshot
from app.models.ram_snapshot import RamSnapshot
from app.models.network_io_snapshot import NetworkIoSnapshot
from app.models.active_connection import ActiveConnection
from app.models.system_log import SystemLog
from app.models.auth_event import AuthEvent
from app.models.visited_site import VisitedSite
from app.models.network_interface import NetworkInterface
from app.models.dns_server import DnsServer
from app.models.routing_entry import RoutingEntry
from app.models.security_status import SecurityStatus

from app.schemas.nodes_read import (
    NodeResponse,
    NodeStatusResponse,
    OsInfoResponse,
    HardwareInfoResponse,
    CpuSnapshotResponse,
    RamSnapshotResponse,
    DiskSnapshotResponse,
    NetworkIoSnapshotResponse,
    ProcessSnapshotResponse,
    ProcessHistoryPageResponse,
    ActiveConnectionsBatchResponse,
    LogBatchResponse,
    BrowserHistoryBatchResponse,
    NetworkConfigBatchResponse,
    SecurityStatusResponse,
    InstalledPackagesBatchResponse,
    OverviewResponse,
    TopDomainResponse,
)

router = APIRouter()

# A node is considered "online" if it's polled for commands within this
# window. The agent polls every 10 seconds, so 30s gives a couple of
# missed-beat tolerance before flipping to offline.
ONLINE_THRESHOLD = timedelta(seconds=30)


def _node_status(node: Node) -> str:
    if not node.last_seen:
        return "offline"
    last_seen = node.last_seen
    if last_seen.tzinfo is None:
        # Defensive: some DB drivers (e.g. SQLite) return naive datetimes
        # even for DateTime(timezone=True) columns. Postgres returns
        # tz-aware values correctly, but this guard costs nothing.
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - last_seen
    return "online" if age <= ONLINE_THRESHOLD else "offline"


def _get_node_or_404(node_id: int, db: Session) -> Node:
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def _node_to_response(node: Node) -> NodeResponse:
    return NodeResponse(
        id=node.id,
        machine_id=node.machine_id,
        hostname=node.hostname,
        status=_node_status(node),
        enrolled_at=node.enrolled_at,
        last_seen=node.last_seen,
    )


# ── Node list / detail / status ─────────────────────────────────────────────

@router.get("/nodes", response_model=List[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    nodes = db.query(Node).order_by(desc(Node.enrolled_at)).all()
    return [_node_to_response(n) for n in nodes]


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(node_id: int, db: Session = Depends(get_db)):
    node = _get_node_or_404(node_id, db)
    return _node_to_response(node)


@router.get("/nodes/{node_id}/status", response_model=NodeStatusResponse)
def get_node_status(node_id: int, db: Session = Depends(get_db)):
    node = _get_node_or_404(node_id, db)
    return NodeStatusResponse(node_id=node.id, status=_node_status(node), last_seen=node.last_seen)


# ── Overview (the "most important + eye-catching" page) ────────────────────

@router.get("/nodes/{node_id}/overview", response_model=OverviewResponse)
def get_node_overview(node_id: int, db: Session = Depends(get_db)):
    node = _get_node_or_404(node_id, db)

    os_info = db.query(OsInfo).filter(OsInfo.node_id == node_id).order_by(desc(OsInfo.received_at)).first()
    hardware_info = db.query(HardwareInfo).filter(HardwareInfo.node_id == node_id).order_by(desc(HardwareInfo.received_at)).first()

    latest_cpu = db.query(CpuSnapshot).filter(CpuSnapshot.node_id == node_id).order_by(desc(CpuSnapshot.received_at)).first()
    latest_ram = db.query(RamSnapshot).filter(RamSnapshot.node_id == node_id).order_by(desc(RamSnapshot.received_at)).first()
    latest_disk = db.query(DiskSnapshot).filter(DiskSnapshot.node_id == node_id).order_by(desc(DiskSnapshot.received_at)).first()
    latest_network_io = db.query(NetworkIoSnapshot).filter(NetworkIoSnapshot.node_id == node_id).order_by(desc(NetworkIoSnapshot.received_at)).first()
    latest_security = db.query(SecurityStatus).filter(SecurityStatus.node_id == node_id).order_by(desc(SecurityStatus.received_at)).first()

    # Top visited domains: take the most recent browser-history batch only
    # (not an all-time sum across every batch ever received), since each
    # batch is already a fresh "most visited" snapshot from the agent.
    latest_history_batch = (
        db.query(VisitedSite.batch_id)
        .filter(VisitedSite.node_id == node_id, VisitedSite.most_visited == 1)
        .order_by(desc(VisitedSite.received_at))
        .first()
    )
    top_domains: List[TopDomainResponse] = []
    if latest_history_batch:
        rows = (
            db.query(VisitedSite)
            .filter(
                VisitedSite.node_id == node_id,
                VisitedSite.batch_id == latest_history_batch[0],
                VisitedSite.most_visited == 1,
            )
            .order_by(desc(VisitedSite.visit_count))
            .limit(5)
            .all()
        )
        top_domains = [
            TopDomainResponse(domain=r.domain, visit_count=r.visit_count or 0, last_visit_time=r.last_visit_time)
            for r in rows
        ]

    # Active connection count: most recent batch only
    latest_conn_batch = (
        db.query(ActiveConnection.batch_id)
        .filter(ActiveConnection.node_id == node_id)
        .order_by(desc(ActiveConnection.received_at))
        .first()
    )
    active_connection_count = 0
    if latest_conn_batch:
        active_connection_count = (
            db.query(ActiveConnection)
            .filter(ActiveConnection.node_id == node_id, ActiveConnection.batch_id == latest_conn_batch[0])
            .count()
        )

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    process_count_last_hour = (
        db.query(ProcessSnapshot)
        .filter(ProcessSnapshot.node_id == node_id, ProcessSnapshot.received_at >= one_hour_ago)
        .count()
    )

    return OverviewResponse(
        node=_node_to_response(node),
        os_info=OsInfoResponse.model_validate(os_info) if os_info else None,
        hardware_info=HardwareInfoResponse.model_validate(hardware_info) if hardware_info else None,
        latest_cpu=CpuSnapshotResponse.model_validate(latest_cpu) if latest_cpu else None,
        latest_ram=RamSnapshotResponse.model_validate(latest_ram) if latest_ram else None,
        latest_disk=DiskSnapshotResponse.model_validate(latest_disk) if latest_disk else None,
        latest_network_io=NetworkIoSnapshotResponse.model_validate(latest_network_io) if latest_network_io else None,
        latest_security=SecurityStatusResponse.model_validate(latest_security) if latest_security else None,
        top_domains=top_domains,
        active_connection_count=active_connection_count,
        process_count_last_hour=process_count_last_hour,
    )


# ── OS / hardware identity ───────────────────────────────────────────────────

@router.get("/nodes/{node_id}/os-info", response_model=OsInfoResponse)
def get_os_info(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(OsInfo).filter(OsInfo.node_id == node_id).order_by(desc(OsInfo.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No OS info received yet")
    return row


@router.get("/nodes/{node_id}/hardware-info", response_model=HardwareInfoResponse)
def get_hardware_info(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(HardwareInfo).filter(HardwareInfo.node_id == node_id).order_by(desc(HardwareInfo.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No hardware info received yet")
    return row


# ── CPU ───────────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/cpu", response_model=CpuSnapshotResponse)
def get_latest_cpu(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(CpuSnapshot).filter(CpuSnapshot.node_id == node_id).order_by(desc(CpuSnapshot.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No CPU data received yet")
    return row


@router.get("/nodes/{node_id}/cpu/history", response_model=List[CpuSnapshotResponse])
def get_cpu_history(node_id: int, limit: int = 60, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    return (
        db.query(CpuSnapshot)
        .filter(CpuSnapshot.node_id == node_id)
        .order_by(desc(CpuSnapshot.received_at))
        .limit(limit)
        .all()
    )


# ── RAM ───────────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/ram", response_model=RamSnapshotResponse)
def get_latest_ram(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(RamSnapshot).filter(RamSnapshot.node_id == node_id).order_by(desc(RamSnapshot.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No RAM data received yet")
    return row


@router.get("/nodes/{node_id}/ram/history", response_model=List[RamSnapshotResponse])
def get_ram_history(node_id: int, limit: int = 60, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    return (
        db.query(RamSnapshot)
        .filter(RamSnapshot.node_id == node_id)
        .order_by(desc(RamSnapshot.received_at))
        .limit(limit)
        .all()
    )


# ── Disk ──────────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/disk", response_model=DiskSnapshotResponse)
def get_latest_disk(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(DiskSnapshot).filter(DiskSnapshot.node_id == node_id).order_by(desc(DiskSnapshot.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No disk data received yet")
    return row


@router.get("/nodes/{node_id}/disk/history", response_model=List[DiskSnapshotResponse])
def get_disk_history(node_id: int, limit: int = 60, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    return (
        db.query(DiskSnapshot)
        .filter(DiskSnapshot.node_id == node_id)
        .order_by(desc(DiskSnapshot.received_at))
        .limit(limit)
        .all()
    )


# ── Network I/O ───────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/network-io", response_model=NetworkIoSnapshotResponse)
def get_latest_network_io(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(NetworkIoSnapshot).filter(NetworkIoSnapshot.node_id == node_id).order_by(desc(NetworkIoSnapshot.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No network I/O data received yet")
    return row


@router.get("/nodes/{node_id}/network-io/history", response_model=List[NetworkIoSnapshotResponse])
def get_network_io_history(node_id: int, limit: int = 60, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    return (
        db.query(NetworkIoSnapshot)
        .filter(NetworkIoSnapshot.node_id == node_id)
        .order_by(desc(NetworkIoSnapshot.received_at))
        .limit(limit)
        .all()
    )


# ── Processes ─────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/processes/history", response_model=ProcessHistoryPageResponse)
def get_process_history(node_id: int, limit: int = 15, offset: int = 0, db: Session = Depends(get_db)):
    """
    Returns recently-seen new processes, most recent first, paginated.
    There's no "latest" single-row endpoint here since each collection
    cycle can report zero-to-many new processes (it's a diff, not a
    snapshot). `total` reflects the full row count for this node so the
    frontend can render page numbers without a separate count call.
    """
    _get_node_or_404(node_id, db)
    base_query = db.query(ProcessSnapshot).filter(ProcessSnapshot.node_id == node_id)
    total = base_query.count()
    items = (
        base_query
        .order_by(desc(ProcessSnapshot.received_at), desc(ProcessSnapshot.id))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ProcessHistoryPageResponse(items=items, total=total, limit=limit, offset=offset)


# ── Active connections (batched) ─────────────────────────────────────────────

@router.get("/nodes/{node_id}/active-connections", response_model=ActiveConnectionsBatchResponse)
def get_latest_active_connections(node_id: int, limit: int = 15, offset: int = 0, db: Session = Depends(get_db)):
    """
    Returns a page of connections from the most recent collection batch.
    `total` is the full connection count in that batch (not just this
    page), so the frontend can render page numbers.
    """
    _get_node_or_404(node_id, db)
    latest = (
        db.query(ActiveConnection)
        .filter(ActiveConnection.node_id == node_id)
        .order_by(desc(ActiveConnection.received_at))
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No connection data received yet")
    batch_query = db.query(ActiveConnection).filter(
        ActiveConnection.node_id == node_id, ActiveConnection.batch_id == latest.batch_id
    )
    total = batch_query.count()
    rows = batch_query.order_by(ActiveConnection.id).offset(offset).limit(limit).all()
    return ActiveConnectionsBatchResponse(
        batch_id=latest.batch_id,
        received_at=latest.received_at,
        connections=rows,
        total=total,
        limit=limit,
        offset=offset,
    )


# ── System logs (batched) ────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/system-logs", response_model=LogBatchResponse)
def get_latest_system_logs(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    latest = db.query(SystemLog).filter(SystemLog.node_id == node_id).order_by(desc(SystemLog.received_at)).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No system logs received yet")
    rows = (
        db.query(SystemLog)
        .filter(SystemLog.node_id == node_id, SystemLog.batch_id == latest.batch_id)
        .order_by(SystemLog.id)
        .all()
    )
    return LogBatchResponse(batch_id=latest.batch_id, received_at=latest.received_at, log_lines=[r.log_line for r in rows])


# ── Auth events (batched) ────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/auth-events", response_model=LogBatchResponse)
def get_latest_auth_events(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    latest = db.query(AuthEvent).filter(AuthEvent.node_id == node_id).order_by(desc(AuthEvent.received_at)).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No auth events received yet")
    rows = (
        db.query(AuthEvent)
        .filter(AuthEvent.node_id == node_id, AuthEvent.batch_id == latest.batch_id)
        .order_by(AuthEvent.id)
        .all()
    )
    return LogBatchResponse(batch_id=latest.batch_id, received_at=latest.received_at, log_lines=[r.log_line for r in rows])


# ── Browser history (batched) ────────────────────────────────────────────────

@router.get("/nodes/{node_id}/browser-history", response_model=BrowserHistoryBatchResponse)
def get_latest_browser_history(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    latest = db.query(VisitedSite).filter(VisitedSite.node_id == node_id).order_by(desc(VisitedSite.received_at)).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No browser history received yet")
    rows = (
        db.query(VisitedSite)
        .filter(VisitedSite.node_id == node_id, VisitedSite.batch_id == latest.batch_id)
        .all()
    )
    most_visited = [r for r in rows if r.most_visited == 1]
    recently_visited = [r for r in rows if r.most_visited == 0]
    most_visited.sort(key=lambda r: r.visit_count or 0, reverse=True)
    recently_visited.sort(key=lambda r: r.last_visit_time or 0, reverse=True)
    return BrowserHistoryBatchResponse(
        batch_id=latest.batch_id,
        received_at=latest.received_at,
        most_visited=most_visited,
        recently_visited=recently_visited,
    )


# ── Network config: interfaces + DNS + routing (batched) ───────────────────

@router.get("/nodes/{node_id}/network-config", response_model=NetworkConfigBatchResponse)
def get_latest_network_config(node_id: int, db: Session = Depends(get_db)):
    """
    Interfaces, DNS servers, and routing table are all collected together
    every 30 minutes by the agent, so we serve them together too.
    """
    _get_node_or_404(node_id, db)
    latest_iface = db.query(NetworkInterface).filter(NetworkInterface.node_id == node_id).order_by(desc(NetworkInterface.received_at)).first()
    if not latest_iface:
        raise HTTPException(status_code=404, detail="No network config received yet")

    interfaces = (
        db.query(NetworkInterface)
        .filter(NetworkInterface.node_id == node_id, NetworkInterface.batch_id == latest_iface.batch_id)
        .all()
    )
    dns_rows = (
        db.query(DnsServer)
        .filter(DnsServer.node_id == node_id, DnsServer.batch_id == latest_iface.batch_id)
        .all()
    )
    routing_rows = (
        db.query(RoutingEntry)
        .filter(RoutingEntry.node_id == node_id, RoutingEntry.batch_id == latest_iface.batch_id)
        .all()
    )
    return NetworkConfigBatchResponse(
        batch_id=latest_iface.batch_id,
        received_at=latest_iface.received_at,
        interfaces=interfaces,
        dns_servers=[r.address for r in dns_rows],
        routing_table=[r.route for r in routing_rows],
    )


# ── Security status ──────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/security-status", response_model=SecurityStatusResponse)
def get_latest_security_status(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    row = db.query(SecurityStatus).filter(SecurityStatus.node_id == node_id).order_by(desc(SecurityStatus.received_at)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No security status received yet")
    return row


@router.get("/nodes/{node_id}/security-status/history", response_model=List[SecurityStatusResponse])
def get_security_status_history(node_id: int, limit: int = 48, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    return (
        db.query(SecurityStatus)
        .filter(SecurityStatus.node_id == node_id)
        .order_by(desc(SecurityStatus.received_at))
        .limit(limit)
        .all()
    )


# ── Installed packages (batched) ─────────────────────────────────────────────

@router.get("/nodes/{node_id}/installed-packages", response_model=InstalledPackagesBatchResponse)
def get_latest_installed_packages(node_id: int, db: Session = Depends(get_db)):
    _get_node_or_404(node_id, db)
    latest = (
        db.query(InstalledPackage)
        .filter(InstalledPackage.node_id == node_id)
        .order_by(desc(InstalledPackage.received_at))
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No installed packages received yet")
    rows = (
        db.query(InstalledPackage)
        .filter(InstalledPackage.node_id == node_id, InstalledPackage.batch_id == latest.batch_id)
        .order_by(InstalledPackage.package_name)
        .all()
    )
    return InstalledPackagesBatchResponse(
        batch_id=latest.batch_id,
        received_at=latest.received_at,
        packages=[r.package_name for r in rows],
    )