"""
Command poll loop — runs in a background daemon thread.

Every 10 seconds:
  1. Evaluate scheduled enforcement rules (window-based, not clock-exact)
  2. Poll the backend for pending commands
  3. Execute each command

The poll request also acts as a heartbeat — the backend marks the node
online when it receives a poll and offline when polls stop arriving.
"""

import time
import json
import requests
import os
from dotenv import load_dotenv

from enforcement.state import get_all_enforcement_state
from enforcement import firewall, scheduler
from collectors.system_profile import collector as system_profile
from collectors.resource_usage import collector as resource_usage
from collectors.process import collector as process_collector
from collectors.network import collector as network
from collectors.security import collector as security
from collectors.logs import collector as logs

load_dotenv()
SERVER_URL = os.getenv("ARGUS_SERVER_URL")

POLL_INTERVAL = 10  # seconds


def _get_headers():
    try:
        with open("credentials.json", "r") as f:
            creds = json.load(f)
        return {
            "Authorization": f"Bearer {creds['api_key']}",
            "Content-Type": "application/json",
        }
    except (FileNotFoundError, KeyError):
        return {"Content-Type": "application/json"}


def _get_node_id():
    try:
        with open("credentials.json", "r") as f:
            return json.load(f)["node_id"]
    except (FileNotFoundError, KeyError):
        return None


def poll_for_commands():
    """
    Polls the server for pending commands.
    Returns a list of command dicts, or [] if server is unreachable.
    Also acts as heartbeat — server tracks last_seen from poll arrival.
    """
    node_id = _get_node_id()
    if node_id is None:
        return []

    url = f"{SERVER_URL}/nodes/{node_id}/commands/pending"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=5)
        response.raise_for_status()
        return response.json().get("commands", [])
    except Exception:
        return []


def _report_result(command_id, success, data=None):
    """Sends command execution result back to the server (best-effort)."""
    node_id = _get_node_id()
    if node_id is None:
        return

    url = f"{SERVER_URL}/nodes/{node_id}/commands/{command_id}/result"
    payload = {
        "node_id": node_id,
        "command_id": command_id,
        "success": success,
        "data": data or {},
    }
    try:
        requests.post(url, json=payload, headers=_get_headers(), timeout=5)
    except Exception:
        pass


def _report_firewall_status(rule_id, command_id, event, success, message=None):
    """
    Reports the outcome of an enforce or delete_rule command back to the
    /firewall-rules/apply-status endpoint so the frontend can show live status
    and the history log is updated.
    """
    node_id = _get_node_id()
    if node_id is None:
        return

    url = f"{SERVER_URL}/nodes/{node_id}/firewall-rules/apply-status"
    payload = {
        "rule_id": rule_id,
        "command_id": command_id,
        "event": event,
        "success": success,
        "message": message,
    }
    try:
        requests.post(url, json=payload, headers=_get_headers(), timeout=5)
    except Exception as e:
        print(f"[poller] Could not report firewall status: {e}", flush=True)


def _execute_command(command):
    """Central dispatcher for all server-initiated commands."""
    command_id = command.get("command_id")
    cmd_type = command.get("type")
    payload = command.get("payload", {})

    print(f"[poller] Executing command: {cmd_type} (id={command_id})", flush=True)

    try:
        if cmd_type == "refresh":
            result = _handle_refresh(payload)
        elif cmd_type == "enforce":
            result = _handle_enforce(payload, command_id)
        elif cmd_type == "delete_rule":
            result = _handle_delete_rule(payload, command_id)
        elif cmd_type == "get_rules":
            result = get_all_enforcement_state()
        else:
            result = {"error": f"Unknown command type: {cmd_type}"}

        _report_result(command_id, success=True, data=result)

    except Exception as e:
        print(f"[poller] Command failed: {e}", flush=True)
        _report_result(command_id, success=False, data={"error": str(e)})


def _handle_refresh(payload):
    """
    Executes a single collector on demand and returns its data.
    """
    collector_name = payload.get("collector")

    collectors = {
        "cpu":                   lambda: resource_usage.get_cpu_usage(),
        "disk":                  lambda: resource_usage.get_disk_usage(),
        "ram":                   lambda: resource_usage.get_ram_usage(),
        "network_io":            lambda: resource_usage.get_network_io(),
        "processes":             lambda: process_collector.get_running_processes(),
        "active_connections":    lambda: network.get_active_connections(),
        "network_interfaces":    lambda: network.get_network_interfaces(),
        "dns_servers":           lambda: network.get_dns_servers(),
        "routing_table":         lambda: network.get_routing_table(),
        "security_status":       lambda: {
            **security.get_firewall_status(),
            **security.get_disk_encryption_status(),
            **security.get_ssh_config_status(),
            **security.get_mac_status(),
        },
        "firewall_rules":        lambda: security.get_firewall_rules(),
        "system_logs":           lambda: logs.get_recent_logs(minutes_back=5),
        "auth_events":           lambda: logs.get_auth_events(minutes_back=5),
        "browser_history":       lambda: {
            "most_visited": logs.get_browser_history(limit=50),
            "recently_visited": logs.get_recently_visited_sites(limit=50),
        },
        "os_info":               lambda: system_profile.get_os_info(),
        "hardware_info":         lambda: system_profile.get_hardware_info(),
        "installed_packages":    lambda: system_profile.get_installed_packages(),
        "all_rules":             lambda: get_all_enforcement_state(),
    }

    if collector_name not in collectors:
        return {"error": f"Unknown collector: {collector_name}"}

    data = collectors[collector_name]()
    return {"collector": collector_name, "data": data}


def _handle_enforce(payload, command_id):
    """Routes an enforce command to the correct enforcement module and reports status."""
    rule_type = payload.get("rule_type")
    action = payload.get("action")
    params = payload.get("params", {})
    schedule_info = payload.get("schedule")
    rule_id = payload.get("rule_id")

    if schedule_info:
        result = scheduler.apply_scheduled_rule(
            rule={"type": rule_type, "action": action, "params": params},
            start_time=schedule_info["start_time"],
            end_time=schedule_info["end_time"],
        )
    else:
        result = scheduler.apply_rule(
            {"type": rule_type, "action": action, "params": params}
        )

    success = result.get("success", False)
    message = result.get("output", "")

    print(f"[poller] Enforce result: success={success} message={message}", flush=True)

    if rule_id is not None:
        _report_firewall_status(
            rule_id=rule_id,
            command_id=command_id,
            event="applied",
            success=success,
            message=message,
        )

    return result


def _handle_delete_rule(payload, command_id):
    """
    Routes a delete command to the correct enforcement module.

    The payload now always carries rule_type / action / params (the same data
    that was used for the original enforce command), so we can build the reverse
    rule without needing any node-side state.
    """
    rule_type = payload.get("rule_type")
    rule_id = payload.get("rule_id")

    # Legacy: old-style UFW rule number
    if rule_type == "firewall":
        result = firewall.delete_rule(payload["rule_number"])
    elif rule_type == "scheduled_rule":
        result = scheduler.delete_scheduled_rule(payload["index"])
    else:
        action = payload.get("action")
        params = payload.get("params", {})
        schedule_info = payload.get("schedule")

        if rule_type and action:
            if schedule_info:
                # Scheduled rule: remove from scheduler state so window won't re-apply
                # and dispatch the reverse immediately if currently active
                result = scheduler.delete_rule_by_definition(
                    rule={"type": rule_type, "action": action, "params": params},
                    schedule_info=schedule_info,
                )
            else:
                reverse_rule = scheduler._build_reverse_rule(
                    {"type": rule_type, "action": action, "params": params}
                )
                result = scheduler._dispatch_rule(reverse_rule)
        else:
            result = {"success": False, "output": f"Unknown rule_type for delete: {rule_type}"}

    success = result.get("success", False)
    message = result.get("output", "")

    print(f"[poller] Delete result: success={success} message={message}", flush=True)

    if rule_id is not None:
        _report_firewall_status(
            rule_id=rule_id,
            command_id=command_id,
            event="deleted",
            success=success,
            message=message,
        )

    return result


def run_poll_loop():
    """
    Main command poll loop — called from agent.py in a daemon thread.

    Every tick:
      1. Evaluate scheduled rules (window-based — never misses an activation)
      2. Poll for new commands
      3. Execute any pending commands
    """
    print("[poller] Command poll loop started.", flush=True)

    while True:
        scheduler.evaluate_scheduled_rules()

        commands = poll_for_commands()
        for command in commands:
            _execute_command(command)

        time.sleep(POLL_INTERVAL)
