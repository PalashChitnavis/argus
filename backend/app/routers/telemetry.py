"""
Telemetry ingestion endpoints — one per data function.

Every endpoint:
  - is authenticated via the node's API key (get_current_node dependency)
  - returns {"status": "ok"} on success
  - uses a batch_id (UUID) to group rows from a single collection cycle
    so the frontend can always retrieve "the latest batch" with a simple
    ORDER BY received_at DESC + GROUP BY batch_id query.

Collection cadence (enforced by the agent scheduler, not by the backend):
  startup          — once on agent start
  cpu              — every 1 minute
  processes        — every 1 minute
  disk             — every 5 minutes
  ram              — every 5 minutes
  network-io       — every 5 minutes
  active-connections — every 5 minutes
  system-logs      — every 5 minutes
  auth-events      — every 5 minutes
  browser-history  — every 10 minutes
  network-interfaces — every 30 minutes
  dns-servers      — every 30 minutes
  routing-table    — every 30 minutes
  security-status  — every 30 minutes
  os-info          — daily
  hardware-info    — daily
  installed-packages — daily
"""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.auth import get_current_node
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

from app.schemas.telemetry import (
    StartupRequest,
    OsInfoRequest,
    HardwareInfoRequest,
    InstalledPackagesRequest,
    CpuRequest,
    ProcessesRequest,
    DiskRequest,
    RamRequest,
    NetworkIoRequest,
    ActiveConnectionsRequest,
    SystemLogsRequest,
    AuthEventsRequest,
    BrowserHistoryRequest,
    NetworkInterfacesRequest,
    DnsServersRequest,
    RoutingTableRequest,
    SecurityStatusRequest,
)

router = APIRouter(prefix="/telemetry")


def _none_str(val):
    """Convert the string 'None' that psutil emits to Python None."""
    if val in ("None", ""):
        return None
    return val


# ── Startup ───────────────────────────────────────────────────────────────────

@router.post("/startup", status_code=201)
def receive_startup(
    req: StartupRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """
    Called once when the agent starts up.
    Stores OS info, hardware specs, and installed packages in one shot.
    """
    if req.os_info:
        db.add(OsInfo(
            node_id=node.id,
            distro_name=req.os_info.distro_name,
            distro_version=req.os_info.distro_version,
            distro_codename=req.os_info.distro_codename,
            distro_id=req.os_info.distro_id,
            kernel_version=req.os_info.kernel_version,
            architecture=req.os_info.architecture,
        ))

    if req.hardware_info:
        db.add(HardwareInfo(
            node_id=node.id,
            cpu_cores_physical=req.hardware_info.cpu_cores_physical,
            cpu_cores_logical=req.hardware_info.cpu_cores_logical,
            ram_total_gb=req.hardware_info.ram_total_gb,
            disk_total_gb=req.hardware_info.disk_total_gb,
        ))

    if req.installed_packages:
        batch = str(uuid.uuid4())
        db.bulk_save_objects([
            InstalledPackage(node_id=node.id, batch_id=batch, package_name=pkg)
            for pkg in req.installed_packages
        ])

    db.commit()
    return {"status": "ok"}


# ── OS info ───────────────────────────────────────────────────────────────────

@router.post("/os-info", status_code=201)
def receive_os_info(
    req: OsInfoRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Collected daily to track kernel/distro updates."""
    db.add(OsInfo(
        node_id=node.id,
        distro_name=req.os_info.distro_name,
        distro_version=req.os_info.distro_version,
        distro_codename=req.os_info.distro_codename,
        distro_id=req.os_info.distro_id,
        kernel_version=req.os_info.kernel_version,
        architecture=req.os_info.architecture,
    ))
    db.commit()
    return {"status": "ok"}


# ── Hardware info ─────────────────────────────────────────────────────────────

@router.post("/hardware-info", status_code=201)
def receive_hardware_info(
    req: HardwareInfoRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Collected daily (rarely changes, but useful for drift detection)."""
    db.add(HardwareInfo(
        node_id=node.id,
        cpu_cores_physical=req.hardware_info.cpu_cores_physical,
        cpu_cores_logical=req.hardware_info.cpu_cores_logical,
        ram_total_gb=req.hardware_info.ram_total_gb,
        disk_total_gb=req.hardware_info.disk_total_gb,
    ))
    db.commit()
    return {"status": "ok"}


# ── Installed packages ────────────────────────────────────────────────────────

@router.post("/installed-packages", status_code=201)
def receive_installed_packages(
    req: InstalledPackagesRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Full package list. Collected daily. All rows share one batch_id."""
    batch = str(uuid.uuid4())
    db.bulk_save_objects([
        InstalledPackage(node_id=node.id, batch_id=batch, package_name=pkg)
        for pkg in req.installed_packages
    ])
    db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.installed_packages)}


# ── CPU ───────────────────────────────────────────────────────────────────────

@router.post("/cpu", status_code=201)
def receive_cpu(
    req: CpuRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """CPU usage percentage. Collected every 1 minute."""
    db.add(CpuSnapshot(node_id=node.id, cpu_percent_used=req.cpu_percent_used))
    db.commit()
    return {"status": "ok"}


# ── Processes ─────────────────────────────────────────────────────────────────

@router.post("/processes", status_code=201)
def receive_processes(
    req: ProcessesRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """
    New processes since the last snapshot (agent diffs internally).
    Collected every 1 minute.
    """
    if req.new_processes:
        db.bulk_save_objects([
            ProcessSnapshot(
                node_id=node.id,
                pid=p.pid,
                create_time=p.create_time,
                name=p.name,
                username=p.username,
                cmdline=p.cmdline,
                status=p.status,
                cpu_percent=p.cpu_percent,
                memory_percent=p.memory_percent,
            )
            for p in req.new_processes
        ])
        db.commit()
    return {"status": "ok", "count": len(req.new_processes)}


# ── Disk ──────────────────────────────────────────────────────────────────────

@router.post("/disk", status_code=201)
def receive_disk(
    req: DiskRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Disk usage. Collected every 5 minutes."""
    db.add(DiskSnapshot(
        node_id=node.id,
        disk_used_gb=req.disk_used_gb,
        disk_free_gb=req.disk_free_gb,
        disk_percent_used=req.disk_percent_used,
    ))
    db.commit()
    return {"status": "ok"}


# ── RAM ───────────────────────────────────────────────────────────────────────

@router.post("/ram", status_code=201)
def receive_ram(
    req: RamRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """RAM usage. Collected every 5 minutes."""
    db.add(RamSnapshot(
        node_id=node.id,
        ram_used_gb=req.ram_used_gb,
        ram_available_gb=req.ram_available_gb,
        ram_percent_used=req.ram_percent_used,
    ))
    db.commit()
    return {"status": "ok"}


# ── Network I/O ───────────────────────────────────────────────────────────────

@router.post("/network-io", status_code=201)
def receive_network_io(
    req: NetworkIoRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Cumulative bytes sent/received. Collected every 5 minutes."""
    db.add(NetworkIoSnapshot(
        node_id=node.id,
        bytes_sent_mb=req.bytes_sent_mb,
        bytes_recv_mb=req.bytes_recv_mb,
    ))
    db.commit()
    return {"status": "ok"}


# ── Active connections ─────────────────────────────────────────────────────────

@router.post("/active-connections", status_code=201)
def receive_active_connections(
    req: ActiveConnectionsRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """All current TCP/UDP connections. Collected every 5 minutes."""
    batch = str(uuid.uuid4())
    if req.connections:
        db.bulk_save_objects([
            ActiveConnection(
                node_id=node.id,
                batch_id=batch,
                local_ip=_none_str(c.local_ip),
                local_port=c.local_port,
                remote_ip=_none_str(c.remote_ip),
                remote_port=c.remote_port,
                status=c.status,
                pid=c.pid,
                process_name=_none_str(c.process_name),
            )
            for c in req.connections
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.connections)}


# ── System logs ───────────────────────────────────────────────────────────────

@router.post("/system-logs", status_code=201)
def receive_system_logs(
    req: SystemLogsRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Recent syslog lines. Collected every 5 minutes."""
    batch = str(uuid.uuid4())
    if req.log_lines:
        db.bulk_save_objects([
            SystemLog(node_id=node.id, batch_id=batch, log_line=line)
            for line in req.log_lines
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.log_lines)}


# ── Auth events ───────────────────────────────────────────────────────────────

@router.post("/auth-events", status_code=201)
def receive_auth_events(
    req: AuthEventsRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Auth log lines (SSH, sudo, su). Collected every 5 minutes."""
    batch = str(uuid.uuid4())
    if req.log_lines:
        db.bulk_save_objects([
            AuthEvent(node_id=node.id, batch_id=batch, log_line=line)
            for line in req.log_lines
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.log_lines)}


# ── Browser history ───────────────────────────────────────────────────────────

@router.post("/browser-history", status_code=201)
def receive_browser_history(
    req: BrowserHistoryRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """
    Browser history — two kinds in one call:
      most_visited    — per-domain aggregates
      recently_visited — individual recent visits
    Collected every 10 minutes.
    """
    batch = str(uuid.uuid4())
    rows = []

    for entry in req.most_visited:
        rows.append(VisitedSite(
            node_id=node.id,
            batch_id=batch,
            most_visited=1,
            domain=entry.domain,
            visit_count=entry.visit_count,
            last_visit_time=entry.last_visit_time,
            browsers=entry.browsers,
            title=entry.title,
        ))

    for entry in req.recently_visited:
        rows.append(VisitedSite(
            node_id=node.id,
            batch_id=batch,
            most_visited=0,
            url=entry.url,
            domain=entry.domain,
            title=entry.title,
            last_visit_time=entry.last_visit_time,
            browser=entry.browser,
        ))

    if rows:
        db.bulk_save_objects(rows)
        db.commit()

    return {
        "status": "ok",
        "batch_id": batch,
        "most_visited_count": len(req.most_visited),
        "recently_visited_count": len(req.recently_visited),
    }


# ── Network interfaces ────────────────────────────────────────────────────────

@router.post("/network-interfaces", status_code=201)
def receive_network_interfaces(
    req: NetworkInterfacesRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Network interface list (IPs, MACs). Collected every 30 minutes."""
    batch = str(uuid.uuid4())
    if req.interfaces:
        db.bulk_save_objects([
            NetworkInterface(
                node_id=node.id,
                batch_id=batch,
                interface_name=i.interface_name,
                ipv4=i.ipv4,
                ipv6=i.ipv6,
                mac_address=i.mac_address,
            )
            for i in req.interfaces
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.interfaces)}


# ── DNS servers ───────────────────────────────────────────────────────────────

@router.post("/dns-servers", status_code=201)
def receive_dns_servers(
    req: DnsServersRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Configured DNS resolvers. Collected every 30 minutes."""
    batch = str(uuid.uuid4())
    if req.dns_servers:
        db.bulk_save_objects([
            DnsServer(node_id=node.id, batch_id=batch, address=addr)
            for addr in req.dns_servers
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.dns_servers)}


# ── Routing table ─────────────────────────────────────────────────────────────

@router.post("/routing-table", status_code=201)
def receive_routing_table(
    req: RoutingTableRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """Routing table entries. Collected every 30 minutes."""
    batch = str(uuid.uuid4())
    if req.routing_table:
        db.bulk_save_objects([
            RoutingEntry(node_id=node.id, batch_id=batch, route=r)
            for r in req.routing_table
        ])
        db.commit()
    return {"status": "ok", "batch_id": batch, "count": len(req.routing_table)}


# ── Security status ───────────────────────────────────────────────────────────

@router.post("/security-status", status_code=201)
def receive_security_status(
    req: SecurityStatusRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node),
):
    """
    Security posture snapshot (firewall, encryption, SSH, MAC).
    Collected every 30 minutes.
    """
    db.add(SecurityStatus(
        node_id=node.id,
        firewall_tool=req.firewall_tool,
        firewall_active=req.firewall_active,
        disk_encrypted=req.disk_encrypted,
        root_login_permitted=req.root_login_permitted,
        password_auth_permitted=req.password_auth_permitted,
        mac_tool=req.mac_tool,
        mac_enabled=req.mac_enabled,
    ))
    db.commit()
    return {"status": "ok"}
