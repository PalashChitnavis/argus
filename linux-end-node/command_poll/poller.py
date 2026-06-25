import time
import requests
import os
from dotenv import load_dotenv

from enforcement.state import get_all_enforcement_state
from enforcement import firewall, hosts, bandwidth, iptables, scheduler
from collectors.system_profile import collector as system_profile
from collectors.resource_usage import collector as resource_usage
from collectors.process import collector as process_collector
from collectors.network import collector as network
from collectors.security import collector as security
from collectors.logs import collector as logs

load_dotenv()
SERVER_URL = os.getenv("ARGUS_SERVER_URL")

# How often we poll for commands, in seconds.
# Short enough to feel responsive (refresh button), long enough
# not to hammer the server.
POLL_INTERVAL = 10


def _get_headers():
    """
    Builds auth headers using the node's registered API key.
    Reads from credentials.json at call time (not at import time)
    so it always uses the current key even if credentials were
    just written during this session.
    """
    try:
        import json
        with open("credentials.json", "r") as f:
            creds = json.load(f)
        return {
            "Authorization": f"Bearer {creds['api_key']}",
            "Content-Type": "application/json",
        }
    except (FileNotFoundError, KeyError):
        return {"Content-Type": "application/json"}


def _get_node_id():
    """Returns the node's registered ID from credentials.json."""
    try:
        import json
        with open("credentials.json", "r") as f:
            return json.load(f)["node_id"]
    except (FileNotFoundError, KeyError):
        return None


def poll_for_commands():
    """
    Polls the server for any pending commands for this node.
    Returns a list of command dicts, or empty list if none pending
    or server is unreachable.

    This call also acts as our heartbeat — the server sees a
    regular poll request and marks the node as online. If polls
    stop arriving, the server marks the node offline. Zero extra
    work needed on our side for heartbeat.
    """
    node_id = _get_node_id()
    if node_id is None:
        return []

    url = f"{SERVER_URL}/nodes/{node_id}/commands/pending"

    try:
        response = requests.get(url, headers=_get_headers(), timeout=5)
        response.raise_for_status()
        return response.json().get("commands", [])

    except requests.exceptions.ConnectionError:
        # Server unreachable — silent, expected during offline periods
        return []
    except requests.exceptions.Timeout:
        return []
    except requests.exceptions.HTTPError:
        return []
    except Exception:
        return []


def _report_result(command_id, success, data=None):
    """
    Sends the result of a command execution back to the server,
    so the frontend can show the outcome (success/failure,
    and any data the command produced).
    """
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
        # Result reporting is best-effort — don't crash if this fails
        pass


def _execute_command(command):
    """
    Routes an incoming command to the correct enforcement or
    collector function and returns the result. This is the central
    dispatcher for all server-initiated actions.
    """
    command_id = command.get("command_id")
    cmd_type = command.get("type")
    payload = command.get("payload", {})

    print(f"[poller] Executing command: {cmd_type} (id={command_id})", flush=True)

    try:
        if cmd_type == "refresh":
            result = _handle_refresh(payload)

        elif cmd_type == "enforce":
            result = _handle_enforce(payload)

        elif cmd_type == "delete_rule":
            result = _handle_delete_rule(payload)

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
    Handles a refresh command — collects fresh data for whichever
    collector the frontend requested and returns it immediately.
    This is what powers the per-block refresh button.
    """
    collector_name = payload.get("collector")

    collectors = {
        "network_interfaces":   lambda: network.get_network_interfaces(),
        "active_connections":   lambda: network.get_active_connections(),
        "dns_servers":          lambda: network.get_dns_servers(),
        "routing_table":        lambda: network.get_routing_table(),
        "disk_usage":           lambda: resource_usage.get_disk_usage(),
        "ram_usage":            lambda: resource_usage.get_ram_usage(),
        "cpu_usage":            lambda: resource_usage.get_cpu_usage(),
        "network_io":           lambda: resource_usage.get_network_io(),
        "running_processes":    lambda: process_collector.get_running_processes(),
        "firewall_status":      lambda: security.get_firewall_status(),
        "firewall_rules":       lambda: security.get_firewall_rules(),
        "all_rules":            lambda: get_all_enforcement_state(),
    }

    if collector_name not in collectors:
        return {"error": f"Unknown collector: {collector_name}"}

    data = collectors[collector_name]()
    return {"collector": collector_name, "data": data}


def _handle_enforce(payload):
    """
    Routes an enforce command to the correct enforcement module.
    """
    rule_type = payload.get("rule_type")
    action = payload.get("action")
    params = payload.get("params", {})
    schedule_info = payload.get("schedule")

    # If this rule has a time window, use the scheduler
    if schedule_info:
        return scheduler.apply_scheduled_rule(
            rule={"type": rule_type, "action": action, "params": params},
            start_time=schedule_info["start_time"],
            end_time=schedule_info["end_time"],
        )

    # Otherwise apply immediately via the dispatcher
    return scheduler.apply_rule(
        {"type": rule_type, "action": action, "params": params}
    )


def _handle_delete_rule(payload):
    """
    Routes a delete command to the correct enforcement module.
    """
    rule_type = payload.get("rule_type")

    if rule_type == "firewall":
        return firewall.delete_rule(payload["rule_number"])

    elif rule_type == "domain":
        return hosts.unblock_domain(payload["domain"])

    elif rule_type == "bandwidth":
        return bandwidth.remove_bandwidth_limit(
            interface=payload.get("interface")
        )

    elif rule_type == "user_block":
        return iptables.unblock_user_network(
            username=payload["username"],
            port=payload.get("port"),
        )

    elif rule_type == "scheduled_rule":
        return scheduler.delete_scheduled_rule(payload["index"])

    return {"success": False, "error": f"Unknown rule_type for delete: {rule_type}"}


def run_poll_loop():
    """
    The main command poll loop — called from agent.py's main().
    Runs in its own thread so it doesn't interfere with the
    existing schedule-based collection loop.
    """
    print("[poller] Command poll loop started.", flush=True)

    while True:
        commands = poll_for_commands()

        for command in commands:
            _execute_command(command)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    import json

    print("=== Command Poller Tests ===\n")

    print("1. Testing _get_node_id()...")
    print(f"   node_id: {_get_node_id()}")

    print("\n2. Testing refresh command dispatch (no server needed)...")
    result = _handle_refresh({"collector": "disk_usage"})
    print(f"   Result: {json.dumps(result, indent=2)}")

    print("\n3. Testing enforce command dispatch...")
    # First enable UFW so rules can be added
    firewall.enable_firewall()
    result = _handle_enforce({
        "rule_type": "port",
        "action": "deny",
        "params": {"port": 9999, "protocol": "tcp"}
    })
    print(f"   Result: {result}")

    print("\n4. Testing delete_rule command dispatch...")
    result = _handle_delete_rule({
        "rule_type": "firewall",
        "rule_number": 1
    })
    print(f"   Result: {result}")

    print("\n5. Testing domain block/delete...")
    result = _handle_enforce({
        "rule_type": "domain",
        "action": "block",
        "params": {"domain": "test-block.com"}
    })
    print(f"   Block result: {result}")

    result = _handle_delete_rule({
        "rule_type": "domain",
        "domain": "test-block.com"
    })
    print(f"   Delete result: {result}")

    print("\n6. Testing get_rules command...")
    result = get_all_enforcement_state()
    print(f"   Rules state: {json.dumps(result, indent=2)}")

    print("\n7. Cleanup — disabling firewall...")
    firewall.disable_firewall()

    print("\nDone.")