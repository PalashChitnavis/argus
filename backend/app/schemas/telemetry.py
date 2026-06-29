from pydantic import BaseModel
from typing import List, Optional


# ── Startup / Daily ─────────────────────────────────────────────────────────

class OsInfoPayload(BaseModel):
    distro_name: Optional[str] = None
    distro_version: Optional[str] = None
    distro_codename: Optional[str] = None
    distro_id: Optional[str] = None
    kernel_version: Optional[str] = None
    architecture: Optional[str] = None


class HardwareInfoPayload(BaseModel):
    cpu_cores_physical: Optional[int] = None
    cpu_cores_logical: Optional[int] = None
    ram_total_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None


class StartupRequest(BaseModel):
    """Sent once on agent startup — registers basic node identity."""
    machine_id: str
    hostname: Optional[str] = None
    os_info: Optional[OsInfoPayload] = None
    hardware_info: Optional[HardwareInfoPayload] = None
    installed_packages: Optional[List[str]] = []


class OsInfoRequest(BaseModel):
    machine_id: str
    os_info: OsInfoPayload


class HardwareInfoRequest(BaseModel):
    machine_id: str
    hardware_info: HardwareInfoPayload


class InstalledPackagesRequest(BaseModel):
    machine_id: str
    installed_packages: List[str] = []


# ── CPU ──────────────────────────────────────────────────────────────────────

class CpuRequest(BaseModel):
    """POST /telemetry/cpu  — every 1 minute."""
    machine_id: str
    cpu_percent_used: Optional[float] = None


# ── Processes ────────────────────────────────────────────────────────────────

class ProcessEntry(BaseModel):
    pid: int
    create_time: float
    name: Optional[str] = None
    username: Optional[str] = None
    cmdline: Optional[str] = None
    status: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None


class ProcessesRequest(BaseModel):
    """POST /telemetry/processes  — every 1 minute (new processes only)."""
    machine_id: str
    new_processes: List[ProcessEntry] = []


# ── Disk ─────────────────────────────────────────────────────────────────────

class DiskRequest(BaseModel):
    """POST /telemetry/disk  — every 5 minutes."""
    machine_id: str
    disk_used_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    disk_percent_used: Optional[float] = None


# ── RAM ──────────────────────────────────────────────────────────────────────

class RamRequest(BaseModel):
    """POST /telemetry/ram  — every 5 minutes."""
    machine_id: str
    ram_used_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_percent_used: Optional[float] = None


# ── Network I/O ──────────────────────────────────────────────────────────────

class NetworkIoRequest(BaseModel):
    """POST /telemetry/network-io  — every 5 minutes."""
    machine_id: str
    bytes_sent_mb: Optional[float] = None
    bytes_recv_mb: Optional[float] = None


# ── Active connections ────────────────────────────────────────────────────────

class ConnectionEntry(BaseModel):
    local_ip: Optional[str] = None
    local_port: Optional[int] = None
    remote_ip: Optional[str] = None
    remote_port: Optional[int] = None
    status: Optional[str] = None
    pid: Optional[int] = None
    process_name: Optional[str] = None


class ActiveConnectionsRequest(BaseModel):
    """POST /telemetry/active-connections  — every 5 minutes."""
    machine_id: str
    connections: List[ConnectionEntry] = []


# ── System logs ───────────────────────────────────────────────────────────────

class SystemLogsRequest(BaseModel):
    """POST /telemetry/system-logs  — every 5 minutes."""
    machine_id: str
    log_lines: List[str] = []


# ── Auth events ───────────────────────────────────────────────────────────────

class AuthEventsRequest(BaseModel):
    """POST /telemetry/auth-events  — every 5 minutes."""
    machine_id: str
    log_lines: List[str] = []


# ── Browser history ───────────────────────────────────────────────────────────

class MostVisitedEntry(BaseModel):
    domain: str
    visit_count: int
    last_visit_time: Optional[float] = None
    browsers: Optional[List[str]] = []
    title: Optional[str] = None


class RecentlyVisitedEntry(BaseModel):
    url: str
    title: Optional[str] = None
    domain: str
    last_visit_time: Optional[float] = None
    browser: str


class BrowserHistoryRequest(BaseModel):
    """POST /telemetry/browser-history  — every 10 minutes."""
    machine_id: str
    most_visited: List[MostVisitedEntry] = []
    recently_visited: List[RecentlyVisitedEntry] = []


# ── Network interfaces ────────────────────────────────────────────────────────

class InterfaceEntry(BaseModel):
    interface_name: Optional[str] = None
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    mac_address: Optional[str] = None


class NetworkInterfacesRequest(BaseModel):
    """POST /telemetry/network-interfaces  — every 30 minutes."""
    machine_id: str
    interfaces: List[InterfaceEntry] = []


# ── DNS servers ───────────────────────────────────────────────────────────────

class DnsServersRequest(BaseModel):
    """POST /telemetry/dns-servers  — every 30 minutes."""
    machine_id: str
    dns_servers: List[str] = []


# ── Routing table ─────────────────────────────────────────────────────────────

class RoutingTableRequest(BaseModel):
    """POST /telemetry/routing-table  — every 30 minutes."""
    machine_id: str
    routing_table: List[str] = []


# ── Security status ───────────────────────────────────────────────────────────

class SecurityStatusRequest(BaseModel):
    """POST /telemetry/security-status  — every 30 minutes."""
    machine_id: str
    firewall_tool: Optional[str] = None
    firewall_active: Optional[bool] = None
    disk_encrypted: Optional[bool] = None
    root_login_permitted: Optional[bool] = None
    password_auth_permitted: Optional[bool] = None
    mac_tool: Optional[str] = None
    mac_enabled: Optional[bool] = None
