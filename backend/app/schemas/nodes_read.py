"""
Response schemas for the read-side API the frontend uses: node list/detail,
the combined overview/dashboard, and per-data-type history.

These mirror the actual snapshot tables in app/models/ (cpu_snapshot,
ram_snapshot, disk_snapshot, network_io_snapshot, active_connection,
system_log, auth_event, visited_site, network_interface, dns_server,
routing_entry, security_status, os_info, hardware_info, installed_package,
process_snapshot) — NOT the old startup/one-minute/five-minute/thirty-minute
tier model from the previous schema version.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# ── Node ──────────────────────────────────────────────────────────────────────

class NodeResponse(BaseModel):
    id: int
    machine_id: str
    hostname: Optional[str] = None
    status: str  # "online" | "offline" — derived from last_seen
    enrolled_at: datetime
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class NodeStatusResponse(BaseModel):
    node_id: int
    status: str
    last_seen: Optional[datetime] = None


# ── OS / hardware (identity — rarely changes) ───────────────────────────────

class OsInfoResponse(BaseModel):
    distro_name: Optional[str] = None
    distro_version: Optional[str] = None
    distro_codename: Optional[str] = None
    distro_id: Optional[str] = None
    kernel_version: Optional[str] = None
    architecture: Optional[str] = None
    received_at: datetime

    class Config:
        from_attributes = True


class HardwareInfoResponse(BaseModel):
    cpu_cores_physical: Optional[int] = None
    cpu_cores_logical: Optional[int] = None
    ram_total_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    received_at: datetime

    class Config:
        from_attributes = True


# ── CPU / RAM / disk / network-io (1 & 5 minute live metrics) ───────────────

class CpuSnapshotResponse(BaseModel):
    id: int
    received_at: datetime
    cpu_percent_used: Optional[float] = None

    class Config:
        from_attributes = True


class RamSnapshotResponse(BaseModel):
    id: int
    received_at: datetime
    ram_used_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_percent_used: Optional[float] = None

    class Config:
        from_attributes = True


class DiskSnapshotResponse(BaseModel):
    id: int
    received_at: datetime
    disk_used_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    disk_percent_used: Optional[float] = None

    class Config:
        from_attributes = True


class NetworkIoSnapshotResponse(BaseModel):
    id: int
    received_at: datetime
    bytes_sent_mb: Optional[float] = None
    bytes_recv_mb: Optional[float] = None

    class Config:
        from_attributes = True


# ── Processes ────────────────────────────────────────────────────────────────

class ProcessSnapshotResponse(BaseModel):
    pid: int
    create_time: float
    name: Optional[str] = None
    username: Optional[str] = None
    cmdline: Optional[str] = None
    status: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    received_at: datetime

    class Config:
        from_attributes = True


class ProcessHistoryPageResponse(BaseModel):
    """Paginated wrapper — `total` is the full row count for this node,
    independent of `limit`/`offset`, so the frontend can render page numbers."""
    items: List[ProcessSnapshotResponse]
    total: int
    limit: int
    offset: int


# ── Active connections (batched) ────────────────────────────────────────────

class ActiveConnectionResponse(BaseModel):
    local_ip: Optional[str] = None
    local_port: Optional[int] = None
    remote_ip: Optional[str] = None
    remote_port: Optional[int] = None
    status: Optional[str] = None
    pid: Optional[int] = None
    process_name: Optional[str] = None

    class Config:
        from_attributes = True


class ActiveConnectionsBatchResponse(BaseModel):
    batch_id: str
    received_at: datetime
    connections: List[ActiveConnectionResponse]
    total: int
    limit: int
    offset: int


# ── System / auth logs (batched) ────────────────────────────────────────────

class LogBatchResponse(BaseModel):
    batch_id: str
    received_at: datetime
    log_lines: List[str]


# ── Browser history (batched) ───────────────────────────────────────────────

class MostVisitedSiteResponse(BaseModel):
    domain: str
    visit_count: int
    last_visit_time: Optional[float] = None
    browsers: Optional[List[str]] = None
    title: Optional[str] = None

    class Config:
        from_attributes = True


class RecentlyVisitedSiteResponse(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    domain: str
    last_visit_time: Optional[float] = None
    browser: Optional[str] = None

    class Config:
        from_attributes = True


class BrowserHistoryBatchResponse(BaseModel):
    batch_id: str
    received_at: datetime
    most_visited: List[MostVisitedSiteResponse]
    recently_visited: List[RecentlyVisitedSiteResponse]


# ── Network config (batched) ────────────────────────────────────────────────

class NetworkInterfaceResponse(BaseModel):
    interface_name: Optional[str] = None
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    mac_address: Optional[str] = None

    class Config:
        from_attributes = True


class NetworkConfigBatchResponse(BaseModel):
    batch_id: str
    received_at: datetime
    interfaces: List[NetworkInterfaceResponse]
    dns_servers: List[str]
    routing_table: List[str]


# ── Security status ──────────────────────────────────────────────────────────

class SecurityStatusResponse(BaseModel):
    received_at: datetime
    firewall_tool: Optional[str] = None
    firewall_active: Optional[bool] = None
    disk_encrypted: Optional[bool] = None
    root_login_permitted: Optional[bool] = None
    password_auth_permitted: Optional[bool] = None
    mac_tool: Optional[str] = None
    mac_enabled: Optional[bool] = None

    class Config:
        from_attributes = True


# ── Installed packages (batched) ────────────────────────────────────────────

class InstalledPackagesBatchResponse(BaseModel):
    batch_id: str
    received_at: datetime
    packages: List[str]


# ── Overview / dashboard ─────────────────────────────────────────────────────

class TopDomainResponse(BaseModel):
    domain: str
    visit_count: int
    last_visit_time: Optional[float] = None


class OverviewResponse(BaseModel):
    """
    Everything the top-of-page summary needs in one call: node identity,
    hardware, current resource usage, security headline, and the most
    eye-catching telemetry (top visited domains, busiest connection).
    """
    node: NodeResponse
    os_info: Optional[OsInfoResponse] = None
    hardware_info: Optional[HardwareInfoResponse] = None

    latest_cpu: Optional[CpuSnapshotResponse] = None
    latest_ram: Optional[RamSnapshotResponse] = None
    latest_disk: Optional[DiskSnapshotResponse] = None
    latest_network_io: Optional[NetworkIoSnapshotResponse] = None
    latest_security: Optional[SecurityStatusResponse] = None

    top_domains: List[TopDomainResponse] = []
    active_connection_count: int = 0
    process_count_last_hour: int = 0