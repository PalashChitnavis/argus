import json
import os
import schedule as sched
import threading

from enforcement import firewall, hosts, bandwidth, iptables

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULED_RULES_FILE = os.path.join(BASE_DIR, "scheduled_rules.json")


def _load_scheduled_rules():
    """Loads persisted scheduled rules from disk."""
    if not os.path.exists(SCHEDULED_RULES_FILE):
        return []
    with open(SCHEDULED_RULES_FILE, "r") as f:
        return json.load(f)


def _save_scheduled_rules(rules):
    """Persists scheduled rules to disk so they survive reboots."""
    with open(SCHEDULED_RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


def _dispatch_rule(rule):
    """
    Takes a rule dict from the server and routes it to the correct
    enforcement function. This is the central dispatcher — all
    enforcement types flow through here.

    Expected rule shape from server:
    {
        "type": "port" | "ip" | "domain" | "bandwidth" | "user_port",
        "action": "allow" | "deny" | "block" | "unblock" | "set" | "remove",
        "params": { ... type-specific fields ... }
    }
    """
    rule_type = rule.get("type")
    action = rule.get("action")
    params = rule.get("params", {})

    print(f"[scheduler] Dispatching rule: type={rule_type} action={action} params={params}", flush=True)

    if rule_type == "port":
        return firewall.add_port_rule(
            action=action,
            port=params["port"],
            protocol=params.get("protocol", "tcp"),
            direction=params.get("direction", "in"),
        )

    elif rule_type == "ip":
        return firewall.add_ip_rule(
            action=action,
            ip=params["ip"],
            direction=params.get("direction", "in"),
        )

    elif rule_type == "domain":
        if action == "block":
            return hosts.block_domain(params["domain"])
        elif action == "unblock":
            return hosts.unblock_domain(params["domain"])

    elif rule_type == "bandwidth":
        if action == "set":
            return bandwidth.set_bandwidth_limit(
                rate_mbit=params["rate_mbit"],
                interface=params.get("interface"),
            )
        elif action == "remove":
            return bandwidth.remove_bandwidth_limit(
                interface=params.get("interface")
            )

    elif rule_type == "user_port":
        if action == "block":
            return iptables.block_user_network(
                username=params["username"],
                port=params.get("port"),
                protocol=params.get("protocol", "tcp"),
            )
        elif action == "unblock":
            return iptables.unblock_user_network(
                username=params["username"],
                port=params.get("port"),
                protocol=params.get("protocol", "tcp"),
            )

    return {"success": False, "output": f"Unknown rule type: {rule_type}"}


def apply_rule(rule):
    """
    Applies a rule immediately. If the rule has a time_window,
    schedules it to also be reversed at the end time.
    """
    result = _dispatch_rule(rule)
    print(f"[scheduler] Rule result: {result}", flush=True)
    return result


def apply_scheduled_rule(rule, start_time, end_time):
    """
    Schedules a rule to be applied at start_time and reversed at end_time.
    Times are strings in "HH:MM" 24-hour format, e.g. "09:00".
    Persists the schedule to disk so it survives reboots.

    The reversal logic builds the opposite action automatically:
    allow -> deny, block -> unblock, set -> remove, etc.
    """
    # Build the reverse rule for the end_time
    reverse_rule = _build_reverse_rule(rule)

    schedule_entry = {
        "rule": rule,
        "reverse_rule": reverse_rule,
        "start_time": start_time,
        "end_time": end_time,
    }

    # Persist so we can reload this on reboot
    existing = _load_scheduled_rules()
    existing.append(schedule_entry)
    _save_scheduled_rules(existing)

    # Register with the schedule library
    _register_scheduled_rule(schedule_entry)

    return {"success": True, "output": f"Scheduled rule from {start_time} to {end_time}"}


def _build_reverse_rule(rule):
    """
    Given a rule, returns the rule that undoes it.
    allow -> deny, block -> unblock, set -> remove, etc.
    """
    reverse_actions = {
        "allow": "deny",
        "deny": "allow",
        "block": "unblock",
        "unblock": "block",
        "set": "remove",
    }

    reverse = dict(rule)  # shallow copy
    reverse["action"] = reverse_actions.get(rule["action"], rule["action"])
    return reverse


def _register_scheduled_rule(entry):
    """
    Registers a schedule entry with the schedule library so it
    fires at the right times. Tagged "argus_scheduled" so we can
    selectively clear just these jobs when deleting rules.
    """
    rule = entry["rule"]
    reverse_rule = entry["reverse_rule"]
    start_time = entry["start_time"]
    end_time = entry["end_time"]

    sched.every().day.at(start_time).do(
        lambda: _dispatch_rule(rule)
    ).tag("argus_scheduled")

    sched.every().day.at(end_time).do(
        lambda: _dispatch_rule(reverse_rule)
    ).tag("argus_scheduled")

    print(f"[scheduler] Registered: apply at {start_time}, reverse at {end_time}", flush=True)


def restore_scheduled_rules():
    """
    Called at agent startup — reloads and re-registers any scheduled
    rules that were active before the agent was restarted or the
    machine was rebooted.
    """
    rules = _load_scheduled_rules()
    for entry in rules:
        _register_scheduled_rule(entry)
    print(f"[scheduler] Restored {len(rules)} scheduled rule(s) from disk", flush=True)

def delete_scheduled_rule(index):
    """
    Deletes a scheduled rule by its index in the persisted list.
    Also cancels the corresponding jobs from the schedule library
    so they don't fire after deletion.

    Index is 0-based, matching the order returned by
    _load_scheduled_rules().
    """
    rules = _load_scheduled_rules()

    if index < 0 or index >= len(rules):
        return {
            "success": False,
            "output": f"No scheduled rule at index {index}. {len(rules)} rule(s) exist."
        }

    removed = rules.pop(index)
    _save_scheduled_rules(rules)

    # Cancel all existing schedule jobs and re-register the
    # remaining ones from scratch. The schedule library has no
    # native "cancel this specific job" API that works cleanly
    # with lambda functions, so clearing and rebuilding the
    # relevant jobs is the safest approach.
    sched.clear("argus_scheduled")
    for entry in rules:
        _register_scheduled_rule(entry)

    return {
        "success": True,
        "output": f"Deleted scheduled rule at index {index}",
        "removed_rule": removed,
    }


if __name__ == "__main__":
    print("=== Scheduler Enforcement Tests ===\n")

    print("1. Applying an immediate port block rule...")
    result = apply_rule({
        "type": "port",
        "action": "deny",
        "params": {"port": 9999, "protocol": "tcp"}
    })
    print(result)

    print("\n2. Checking ufw status to confirm rule was added...")
    import subprocess
    r = subprocess.run(["ufw", "status", "numbered"],
                       capture_output=True, text=True)
    print(r.stdout)

    print("\n3. Applying an immediate domain block...")
    result = apply_rule({
        "type": "domain",
        "action": "block",
        "params": {"domain": "example.com"}
    })
    print(result)

    print("\n4. Registering a time-based rule (apply now + 1 min, reverse + 2 min)...")
    from datetime import datetime, timedelta
    now = datetime.now()
    start = (now + timedelta(minutes=1)).strftime("%H:%M")
    end = (now + timedelta(minutes=2)).strftime("%H:%M")
    result = apply_scheduled_rule(
        rule={"type": "domain", "action": "block", "params": {"domain": "reddit.com"}},
        start_time=start,
        end_time=end,
    )
    print(result)
    print(f"   Scheduled: block reddit.com at {start}, unblock at {end}")

    print("\n5. Checking scheduled_rules.json was written...")
    import json
    with open("scheduled_rules.json") as f:
        print(json.dumps(json.load(f), indent=2))

    print("\n6. Cleaning up — removing test rules...")

    # Remove the port rule we added
    import subprocess
    subprocess.run(["ufw", "--force", "delete", "1"], capture_output=True)

    # Remove domain blocks
    from enforcement.hosts import unblock_domain, clear_all_blocks
    print(unblock_domain("example.com"))
    print(clear_all_blocks())

    # Clean up scheduled_rules.json
    os.remove("scheduled_rules.json")
    print("\nCleanup done.")