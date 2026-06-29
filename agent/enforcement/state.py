from enforcement import firewall, hosts, bandwidth, iptables, scheduler
from collectors.security import collector as security
import json
import os


def get_all_enforcement_state():
    """
    Returns a single consolidated dict representing everything
    currently enforced on this node — firewall rules, blocked
    domains, bandwidth limits, per-user blocks, and scheduled rules.
    This is what the frontend calls when it loads the rules panel,
    or when the admin clicks refresh on the rules block.
    """
    return {
        "firewall": _get_firewall_state(),
        "domains": _get_domain_state(),
        "bandwidth": _get_bandwidth_state(),
        "user_blocks": _get_user_block_state(),
        "scheduled_rules": _get_scheduled_rules_state(),
    }


def _get_firewall_state():
    """
    UFW status + all current rules in one block.
    """
    try:
        status = security.get_firewall_status()
        rules = security.get_firewall_rules()
        return {
            "active": status.get("firewall_active"),
            "rules": rules,
        }
    except Exception as e:
        return {"active": None, "rules": [], "error": str(e)}


def _get_domain_state():
    """
    All domains currently blocked via /etc/hosts by argus.
    """
    try:
        blocked = hosts.list_blocked_domains()
        return {"blocked_domains": blocked}
    except Exception as e:
        return {"blocked_domains": [], "error": str(e)}


def _get_bandwidth_state():
    """
    Current bandwidth limit status on the active interface.
    """
    try:
        return bandwidth.get_bandwidth_limit()
    except Exception as e:
        return {"limited": False, "error": str(e)}


def _get_user_block_state():
    """
    All per-user iptables OUTPUT DROP rules currently active.
    """
    try:
        rules = iptables.list_user_blocks()
        return {"rules": rules}
    except Exception as e:
        return {"rules": [], "error": str(e)}


def _get_scheduled_rules_state():
    """
    All time-based rules currently persisted on disk.
    """
    try:
        rules = scheduler._load_scheduled_rules()
        return {"rules": rules}
    except Exception as e:
        return {"rules": [], "error": str(e)}


if __name__ == "__main__":
    import json

    print("=== Full Enforcement State ===\n")
    state = get_all_enforcement_state()
    print(json.dumps(state, indent=2))