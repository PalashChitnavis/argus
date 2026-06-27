from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Node Responses
class NodeResponse(BaseModel):
    id: int
    machine_id: str
    hostname: str
    registered_at: datetime
    last_seen: Optional[datetime]
    status: str

    class Config:
        from_attributes = True

# Startup Data Response
class InstalledPackageResponse(BaseModel):
    package_name: str

    class Config:
        from_attributes = True

class StartupDataResponse(BaseModel):
    id: int
    node_id: int
    received_at: datetime
    distro_name: Optional[str]
    distro_version: Optional[str]
    kernel_version: Optional[str]
    architecture: Optional[str]
    cpu_cores_physical: Optional[int]
    cpu_cores_logical: Optional[int]
    ram_total_gb: Optional[float]
    disk_total_gb: Optional[float]
    # ORM relationship on StartupData model is called `packages`
    packages: List[InstalledPackageResponse] = []

    class Config:
        from_attributes = True

# One Minute Data Response
class NewProcessResponse(BaseModel):
    pid: int
    name: str
    username: Optional[str]
    cmdline: Optional[str]
    cpu_percent: Optional[float]
    memory_percent: Optional[float]

    class Config:
        from_attributes = True

class OneMinuteDataResponse(BaseModel):
    id: int
    node_id: int
    received_at: datetime
    cpu_percent_used: Optional[float]
    new_processes: List[NewProcessResponse] = []

    class Config:
        from_attributes = True

# Five Minute Data Response
class NetworkConnectionResponse(BaseModel):
    local_ip: Optional[str]
    local_port: Optional[int]
    remote_ip: Optional[str]
    remote_port: Optional[int]
    status: str
    process_name: Optional[str]

    class Config:
        from_attributes = True

class RecentLogResponse(BaseModel):
    log_line: str

    class Config:
        from_attributes = True

class AuthEventResponse(BaseModel):
    log_line: str

    class Config:
        from_attributes = True

class FiveMinuteDataResponse(BaseModel):
    id: int
    node_id: int
    received_at: datetime
    disk_used_gb: Optional[float]
    disk_free_gb: Optional[float]
    disk_percent_used: Optional[float]
    ram_used_gb: Optional[float]
    ram_available_gb: Optional[float]
    ram_percent_used: Optional[float]
    bytes_sent_mb: Optional[float]
    bytes_recv_mb: Optional[float]
    connections: List[NetworkConnectionResponse] = []
    # ORM relationship is `recent_logs`, not `logs`
    recent_logs: List[RecentLogResponse] = []
    auth_events: List[AuthEventResponse] = []

    class Config:
        from_attributes = True

# Thirty Minute Data Response
class NetworkInterfaceResponse(BaseModel):
    interface_name: str
    ipv4: Optional[str]
    ipv6: Optional[str]
    mac_address: Optional[str]

    class Config:
        from_attributes = True

class DnsServerResponse(BaseModel):
    address: str

    class Config:
        from_attributes = True

class RoutingEntryResponse(BaseModel):
    route: str

    class Config:
        from_attributes = True

class ThirtyMinuteDataResponse(BaseModel):
    id: int
    node_id: int
    received_at: datetime
    firewall_tool: Optional[str]
    firewall_active: Optional[bool]
    disk_encrypted: Optional[bool]
    root_login_permitted: Optional[bool]
    password_auth_permitted: Optional[bool]
    mac_tool: Optional[str]
    mac_enabled: Optional[bool]
    interfaces: List[NetworkInterfaceResponse] = []
    dns_servers: List[DnsServerResponse] = []
    routing_table: List[RoutingEntryResponse] = []

    class Config:
        from_attributes = True

# Daily Data Response
class DailyDataResponse(BaseModel):
    id: int
    node_id: int
    received_at: datetime
    distro_name: Optional[str]
    distro_version: Optional[str]
    kernel_version: Optional[str]
    architecture: Optional[str]
    cpu_cores_physical: Optional[int]
    cpu_cores_logical: Optional[int]
    ram_total_gb: Optional[float]
    disk_total_gb: Optional[float]
    # ORM relationship on DailyData model is called `packages`
    packages: List[InstalledPackageResponse] = []

    class Config:
        from_attributes = True