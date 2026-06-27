from pydantic import BaseModel
from typing import List, Optional

# --- Startup ---
class OsInfo(BaseModel):
    distro_name: Optional[str] = None
    distro_version: Optional[str] = None
    distro_codename: Optional[str] = None
    distro_id: Optional[str] = None
    kernel_version: Optional[str] = None
    architecture: Optional[str] = None

class HardwareInfo(BaseModel):
    cpu_cores_physical: Optional[int] = None
    cpu_cores_logical: Optional[int] = None
    ram_total_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None

class StartupDataRequest(BaseModel):
    machine_id: str
    hostname: Optional[str] = None
    os_info: Optional[OsInfo] = None
    hardware_info: Optional[HardwareInfo] = None
    installed_packages: Optional[List[str]] = []

# --- One Minute ---
class CpuUsage(BaseModel):
    cpu_percent_used: Optional[float] = None

class ProcessEntry(BaseModel):
    pid: int
    create_time: float
    name: Optional[str] = None
    username: Optional[str] = None
    cmdline: Optional[str] = None
    status: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None

class OneMinuteDataRequest(BaseModel):
    machine_id: str
    cpu_usage: Optional[CpuUsage] = None
    new_processes: Optional[List[ProcessEntry]] = []

# --- Five Minute ---
class DiskUsage(BaseModel):
    disk_used_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    disk_percent_used: Optional[float] = None

class RamUsage(BaseModel):
    ram_used_gb: Optional[float] = None
    ram_available_gb: Optional[float] = None
    ram_percent_used: Optional[float] = None

class NetworkIo(BaseModel):
    bytes_sent_mb: Optional[float] = None
    bytes_recv_mb: Optional[float] = None

class ConnectionEntry(BaseModel):
    local_ip: Optional[str] = None
    local_port: Optional[int] = None
    remote_ip: Optional[str] = None
    remote_port: Optional[int] = None
    status: Optional[str] = None
    pid: Optional[int] = None
    process_name: Optional[str] = None

class FiveMinuteDataRequest(BaseModel):
    machine_id: str
    disk_usage: Optional[DiskUsage] = None
    ram_usage: Optional[RamUsage] = None
    network_io: Optional[NetworkIo] = None
    connections: Optional[List[ConnectionEntry]] = []
    recent_logs: Optional[List[str]] = []
    auth_events: Optional[List[str]] = []

# --- Thirty Minute ---
class InterfaceEntry(BaseModel):
    interface_name: Optional[str] = None
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    mac_address: Optional[str] = None

class FirewallStatus(BaseModel):
    firewall_tool: Optional[str] = None
    firewall_active: Optional[bool] = None

class DiskEncryption(BaseModel):
    disk_encrypted: Optional[bool] = None

class SshConfig(BaseModel):
    root_login_permitted: Optional[bool] = None
    password_auth_permitted: Optional[bool] = None

class MacStatus(BaseModel):
    mac_tool: Optional[str] = None
    mac_enabled: Optional[bool] = None

class ThirtyMinuteDataRequest(BaseModel):
    machine_id: str
    interfaces: Optional[List[InterfaceEntry]] = []
    dns_servers: Optional[List[str]] = []
    routing_table: Optional[List[str]] = []
    firewall_status: Optional[FirewallStatus] = None
    disk_encryption: Optional[DiskEncryption] = None
    ssh_config: Optional[SshConfig] = None
    mac_status: Optional[MacStatus] = None

# --- Daily ---
class DailyDataRequest(BaseModel):
    machine_id: str
    os_info: Optional[OsInfo] = None
    hardware_info: Optional[HardwareInfo] = None
    installed_packages: Optional[List[str]] = []