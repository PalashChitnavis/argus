# This module previously defined old-style firewall schemas (protocol/source_ip/etc).
# The canonical schemas now live in firewall_commands.py (rule_type/params style).
# Everything is re-exported here for backward compatibility.
from app.schemas.firewall_commands import (
    FirewallRuleBase,
    FirewallRuleCreate,
    FirewallRuleUpdate,
    FirewallRuleResponse,
    FirewallRuleUpdateRequest,
    FirewallStatusResponse,
    ScheduleInfo,
)

__all__ = [
    "FirewallRuleBase",
    "FirewallRuleCreate",
    "FirewallRuleUpdate",
    "FirewallRuleResponse",
    "FirewallRuleUpdateRequest",
    "FirewallStatusResponse",
    "ScheduleInfo",
]