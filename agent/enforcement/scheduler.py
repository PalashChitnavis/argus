import json
import os
from datetime import datetime

from enforcement import firewall, hosts, bandwidth, iptables

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULED_RULES_FILE = os.path.join(BASE_DIR, "scheduled_rules.json")


# ── persistence ──────────────────────────────────────────────────────────────

def _load_scheduled_rules():
    if not os.path.exists(SCHEDULED_RULES_FILE):
        return []
    with open(SCHEDULED_RULES_FILE, "r") as f:
        return json.load(f)


def _save_scheduled_rules(rules):
    with open(SCHEDULED_RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


# ── dispatch ─────────────────────────────────────────────────────────────────

def _dispatch_rule(rule):
    """
    Routes a rule dict to the correct enforcement function.

    Rule shape:
    {
        "type": "port" | "ip" | "domain" | "bandwidth" | "user_port",
        "action": "allow" | "deny" | "block" | "unblock" | "set" | "remove",
        "params": { ... }
    }
    """
    rule_type = rule.get("type")
    action    = rule.get("action")
    params    = rule.get("params", {})

    print(f"[scheduler] Dispatching: type={rule_type} action={action} params={params}", flush=True)

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


def _build_reverse_rule(rule):
    """Returns the rule that undoes the given rule."""
    reverse_actions = {
        "allow":   "deny",
        "deny":    "allow",
        "block":   "unblock",
        "unblock": "block",
        "set":     "remove",
    }
    reverse = dict(rule)
    reverse["action"] = reverse_actions.get(rule["action"], rule["action"])
    return reverse


# ── immediate apply ───────────────────────────────────────────────────────────

def apply_rule(rule):
    """Applies a rule immediately with no time window."""
    result = _dispatch_rule(rule)
    print(f"[scheduler] Rule result: {result}", flush=True)
    return result


# ── window-based scheduling ───────────────────────────────────────────────────

def apply_scheduled_rule(rule, start_time, end_time):
    """
    Registers a rule with a time window [start_time, end_time] (HH:MM, 24h).
    Does NOT apply immediately — the poll loop calls evaluate_scheduled_rules()
    every 10 seconds and enforces based on whether now is inside the window.

    Each entry also tracks `active` so we only apply/reverse on transitions,
    not on every tick inside the window.
    """
    reverse_rule = _build_reverse_rule(rule)

    entry = {
        "rule":         rule,
        "reverse_rule": reverse_rule,
        "start_time":   start_time,
        "end_time":     end_time,
        "active":       False,   # False = rule not currently applied
    }

    existing = _load_scheduled_rules()
    existing.append(entry)
    _save_scheduled_rules(existing)

    print(f"[scheduler] Registered window rule: {start_time} → {end_time}", flush=True)
    return {"success": True, "output": f"Scheduled: active {start_time}–{end_time}"}


def evaluate_scheduled_rules():
    """
    Called on every poll cycle (every 10 s).
    For each saved rule, checks if current time is inside [start_time, end_time]:
      - If inside window and not yet active  → apply rule, mark active=True
      - If outside window and currently active → reverse rule, mark active=False
    State is written back to disk after any change.
    """
    rules = _load_scheduled_rules()
    if not rules:
        return

    now = datetime.now().strftime("%H:%M")
    changed = False

    for entry in rules:
        start = entry["start_time"]
        end   = entry["end_time"]
        in_window = start <= now <= end   # simple string compare works for HH:MM

        if in_window and not entry.get("active", False):
            print(f"[scheduler] Window open ({start}–{end}), applying rule.", flush=True)
            _dispatch_rule(entry["rule"])
            entry["active"] = True
            changed = True

        elif not in_window and entry.get("active", False):
            print(f"[scheduler] Window closed ({start}–{end}), reversing rule.", flush=True)
            _dispatch_rule(entry["reverse_rule"])
            entry["active"] = False
            changed = True

    if changed:
        _save_scheduled_rules(rules)


def delete_scheduled_rule(index):
    """
    Deletes a scheduled rule by its index.
    If the rule is currently active, reverses it first so the
    machine isn't left in an enforced state with no way to undo it.
    """
    rules = _load_scheduled_rules()

    if index < 0 or index >= len(rules):
        return {
            "success": False,
            "output": f"No scheduled rule at index {index}. {len(rules)} rule(s) exist.",
        }

    entry = rules[index]

    # If currently active, undo the rule before deleting
    if entry.get("active", False):  # old entries without this field default to False
        print(f"[scheduler] Rule {index} is active — reversing before delete.", flush=True)
        _dispatch_rule(entry["reverse_rule"])

    removed = rules.pop(index)
    _save_scheduled_rules(rules)

    return {
        "success": True,
        "output": f"Deleted scheduled rule at index {index}",
        "removed_rule": removed,
    }


def restore_scheduled_rules():
    """
    Called at agent startup. Re-evaluates all saved rules immediately
    so windows that were open during a reboot get applied right away.
    No re-registration needed — the poll loop calls evaluate_scheduled_rules()
    every 10 s automatically.
    """
    rules = _load_scheduled_rules()
    print(f"[scheduler] Loaded {len(rules)} scheduled rule(s) from disk.", flush=True)
    # Evaluate immediately so any open window is enforced without waiting
    evaluate_scheduled_rules()

def delete_rule_by_definition(rule, schedule_info):
    """
    Removes a scheduled rule by matching its definition (type+action+params),
    and dispatches the reverse rule if it was currently active.
    Used when a delete_rule command arrives for a rule that had a schedule.
    """
    rules = _load_scheduled_rules()
    target_type = rule.get("type")
    target_action = rule.get("action")
    target_params = rule.get("params", {})

    new_rules = []
    removed = False
    for entry in rules:
        r = entry.get("rule", {})
        match = (
            r.get("type") == target_type
            and r.get("action") == target_action
            and r.get("params") == target_params
        )
        if match and not removed:
            removed = True
            if entry.get("active", False):
                print(f"[scheduler] Scheduled rule is active — reversing before delete.", flush=True)
                _dispatch_rule(entry["reverse_rule"])
        else:
            new_rules.append(entry)

    if removed:
        _save_scheduled_rules(new_rules)
        return {"success": True, "output": "Scheduled rule deleted and reversed if active"}

    # Rule not found in scheduler state — still try to reverse it now
    reverse_rule = _build_reverse_rule({"type": target_type, "action": target_action, "params": target_params})
    result = _dispatch_rule(reverse_rule)
    return result
