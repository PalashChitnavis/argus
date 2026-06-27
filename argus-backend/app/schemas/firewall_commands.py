from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ============ Rule Parameters by Type ============

class PortParams(BaseModel):
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., description="tcp, udp, or any")
    direction: str = Field(..., description="in or out")

class IpParams(BaseModel):
    ip: str = Field(..., description="IP address or CIDR")
    direction: str = Field(..., description="in or out")

class IpPortParams(BaseModel):
    ip: str = Field(..., description="IP address or CIDR")
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., description="tcp or udp")
    direction: str = Field(..., description="in or out")

class DomainParams(BaseModel):
    domain: str = Field(..., description="Domain name to block")

class BandwidthParams(BaseModel):
    rate_mbit: float = Field(..., gt=0, description="Rate limit in Mbps")
    interface: str = Field(..., description="Network interface (e.g., eth0, wlan0)")

class UserPortParams(BaseModel):
    username: str
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., description="tcp or udp")

class ScheduleInfo(BaseModel):
    start_time: str = Field(..., description="HH:MM format")
    end_time: str = Field(..., description="HH:MM format")

# ============ Firewall Rule Schemas - Updated ============

class FirewallRuleBase(BaseModel):
    rule_type: str = Field(..., description="port, ip, ip_port, domain, bandwidth, or user_port")
    action: str = Field(..., description="allow, deny, block, unblock, set, or remove")
    params: Dict[str, Any]
    schedule: Optional[ScheduleInfo] = None
    enabled: bool = True
    description: Optional[str] = None

class FirewallRuleCreate(FirewallRuleBase):
    pass

class FirewallRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    action: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    schedule: Optional[ScheduleInfo] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None

class FirewallRuleResponse(FirewallRuleBase):
    id: int
    node_id: int
    applied: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FirewallStatusResponse(BaseModel):
    node_id: int
    total_rules: int
    enabled_rules: int
    applied_rules: int
    pending_rules: int
    rules_by_type: Dict[str, int] = {}

class FirewallRuleUpdateRequest(BaseModel):
    """Request format for linux-end-node to report firewall rule status"""
    rule_id: int
    applied: bool
    status: str  # "success", "failed", etc.

# ============ Command Schemas ============

class RefreshCommandPayload(BaseModel):
    collector: str = Field(..., description="network_interfaces, active_connections, firewall_status, etc.")

class EnforceCommandPayload(BaseModel):
    rule_type: str = Field(..., description="port, ip, ip_port, domain, bandwidth, user_port")
    action: str
    params: Dict[str, Any]
    schedule: Optional[ScheduleInfo] = None

class DeleteRuleCommandPayload(BaseModel):
    rule_type: str
    rule_number: Optional[int] = None
    domain: Optional[str] = None
    interface: Optional[str] = None
    username: Optional[str] = None
    port: Optional[int] = None
    index: Optional[int] = None

class GetRulesCommandPayload(BaseModel):
    pass

class CommandOut(BaseModel):
    command_id: str
    type: str = Field(..., description="refresh, enforce, delete_rule, get_rules")
    payload: Dict[str, Any]

class PendingCommandsResponse(BaseModel):
    commands: List[CommandOut]

class CommandResultRequest(BaseModel):
    node_id: int
    command_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

# ============ Enforcement State Response (for get_rules command) ============

class FirewallRuleStateOut(BaseModel):
    rule_number: int
    target: str
    action: str
    direction: str

class FirewallState(BaseModel):
    active: bool
    rules: List[FirewallRuleStateOut]

class DomainBlockState(BaseModel):
    blocked_domains: List[str]

class BandwidthLimitState(BaseModel):
    interface: str
    limited: bool
    rate_mbit: Optional[float] = None
    tc_output: Optional[str] = None

class UserBlockRule(BaseModel):
    line_number: int
    target: str
    protocol: str
    uid: int
    username: str
    port: int

class UserBlockState(BaseModel):
    rules: List[UserBlockRule]

class ScheduledRuleItem(BaseModel):
    rule: Dict[str, Any]
    reverse_rule: Dict[str, Any]
    start_time: str
    end_time: str

class ScheduledRulesState(BaseModel):
    rules: List[ScheduledRuleItem]

class EnforcementStateResponse(BaseModel):
    """Response to get_rules command"""
    firewall: FirewallState
    domains: DomainBlockState
    bandwidth: BandwidthLimitState
    user_blocks: UserBlockState
    scheduled_rules: ScheduledRulesState
