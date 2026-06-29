"""
Argus Linux endpoint agent.

Architecture
------------
Each telemetry function has its own endpoint and its own collection interval.
There are no "1-min bucket" or "5-min bucket" concepts — data is organized
by what it IS, not when it was collected.

Collection schedule
-------------------
  startup             — once on agent start
  cpu                 — every 1 min
  processes           — every 1 min
  disk                — every 5 min
  ram                 — every 5 min
  network-io          — every 5 min
  active-connections  — every 5 min
  system-logs         — every 5 min
  auth-events         — every 5 min
  browser-history     — every 10 min
  network-interfaces  — every 30 min
  dns-servers         — every 30 min
  routing-table       — every 30 min
  security-status     — every 30 min
  os-info             — every 24 hr
  hardware-info       — every 24 hr
  installed-packages  — every 24 hr

  retry queue         — every 2 min
  command poll        — every 10 sec (in background thread)
"""

import time
import sys
import threading
import schedule

from collectors.system_profile import collector as system_profile
from collectors.resource_usage import collector as resource_usage
from collectors.process import collector as process_collector
from collectors.network import collector as network
from collectors.security import collector as security
from collectors.logs import collector as logs
from transport.sender import send_data, retry_queued_sends
from registration.register import is_registered, load_credentials, register_node
from command_poll.poller import run_poll_loop
from enforcement.scheduler import restore_scheduled_rules


# ── Process snapshot state ────────────────────────────────────────────────────
# The agent keeps a running snapshot of processes so it can diff and only
# send *new* processes each cycle, instead of the full list every minute.

_last_process_snapshot = []


# ── Individual collection functions ──────────────────────────────────────────

def collect_startup():
    """
    Sent once on agent start.
    Combines OS info, hardware, and installed packages in a single request
    so the backend can store them all atomically.
    """
    global _last_process_snapshot
    print("[agent] Running startup collection...", flush=True)

    payload = {
        "machine_id": system_profile.get_machine_id(),
        "hostname": system_profile.get_hostname(),
        "os_info": system_profile.get_os_info(),
        "hardware_info": system_profile.get_hardware_info(),
        "installed_packages": system_profile.get_installed_packages(),
    }
    ok = send_data("telemetry/startup", payload)
    print(f"[agent] startup → {'ok' if ok else 'FAILED'}", flush=True)

    # Seed the process snapshot so the first diff produces an empty list
    # (we don't want to flood the server with every running process on startup).
    _last_process_snapshot = process_collector.get_running_processes()
    print(f"[agent] Initial process snapshot: {len(_last_process_snapshot)} processes", flush=True)


def collect_cpu():
    """CPU usage percentage — every 1 minute."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        **resource_usage.get_cpu_usage(),   # {"cpu_percent_used": 12.3}
    }
    ok = send_data("telemetry/cpu", payload)
    print(f"[agent] cpu → {'ok' if ok else 'FAILED'}", flush=True)


def collect_processes():
    """New processes since the last snapshot — every 1 minute."""
    global _last_process_snapshot
    current = process_collector.get_running_processes()
    new_procs = process_collector.diff_process_snapshots(_last_process_snapshot, current)
    _last_process_snapshot = current

    if not new_procs:
        print("[agent] processes → nothing new", flush=True)
        return

    payload = {
        "machine_id": system_profile.get_machine_id(),
        "new_processes": new_procs,
    }
    ok = send_data("telemetry/processes", payload)
    print(f"[agent] processes → {'ok' if ok else 'FAILED'} ({len(new_procs)} new)", flush=True)


def collect_disk():
    """Disk usage — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        **resource_usage.get_disk_usage(),
    }
    ok = send_data("telemetry/disk", payload)
    print(f"[agent] disk → {'ok' if ok else 'FAILED'}", flush=True)


def collect_ram():
    """RAM usage — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        **resource_usage.get_ram_usage(),
    }
    ok = send_data("telemetry/ram", payload)
    print(f"[agent] ram → {'ok' if ok else 'FAILED'}", flush=True)


def collect_network_io():
    """Network bytes sent/received — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        **resource_usage.get_network_io(),
    }
    ok = send_data("telemetry/network-io", payload)
    print(f"[agent] network-io → {'ok' if ok else 'FAILED'}", flush=True)


def collect_active_connections():
    """Active TCP/UDP connections — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "connections": network.get_active_connections(),
    }
    ok = send_data("telemetry/active-connections", payload)
    print(f"[agent] active-connections → {'ok' if ok else 'FAILED'}", flush=True)


def collect_system_logs():
    """Recent syslog lines — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "log_lines": logs.get_recent_logs(minutes_back=5),
    }
    ok = send_data("telemetry/system-logs", payload)
    print(f"[agent] system-logs → {'ok' if ok else 'FAILED'}", flush=True)


def collect_auth_events():
    """Auth log lines (SSH, sudo) — every 5 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "log_lines": logs.get_auth_events(minutes_back=5),
    }
    ok = send_data("telemetry/auth-events", payload)
    print(f"[agent] auth-events → {'ok' if ok else 'FAILED'}", flush=True)


def collect_browser_history():
    """
    Browser history — every 10 minutes.
    Sends both most-visited domains and recently-visited individual URLs.
    """
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "most_visited": logs.get_browser_history(limit=50),
        "recently_visited": logs.get_recently_visited_sites(limit=50),
    }
    ok = send_data("telemetry/browser-history", payload)
    print(f"[agent] browser-history → {'ok' if ok else 'FAILED'}", flush=True)


def collect_network_interfaces():
    """Network interfaces (IPs, MACs) — every 30 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "interfaces": network.get_network_interfaces(),
    }
    ok = send_data("telemetry/network-interfaces", payload)
    print(f"[agent] network-interfaces → {'ok' if ok else 'FAILED'}", flush=True)


def collect_dns_servers():
    """Configured DNS resolvers — every 30 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "dns_servers": network.get_dns_servers(),
    }
    ok = send_data("telemetry/dns-servers", payload)
    print(f"[agent] dns-servers → {'ok' if ok else 'FAILED'}", flush=True)


def collect_routing_table():
    """Routing table — every 30 minutes."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "routing_table": network.get_routing_table(),
    }
    ok = send_data("telemetry/routing-table", payload)
    print(f"[agent] routing-table → {'ok' if ok else 'FAILED'}", flush=True)


def collect_security_status():
    """
    Security posture (firewall, disk encryption, SSH config, MAC) —
    every 30 minutes.
    """
    fw = security.get_firewall_status() or {}
    enc = security.get_disk_encryption_status() or {}
    ssh = security.get_ssh_config_status() or {}
    mac = security.get_mac_status() or {}

    payload = {
        "machine_id": system_profile.get_machine_id(),
        "firewall_tool": fw.get("firewall_tool"),
        "firewall_active": fw.get("firewall_active"),
        "disk_encrypted": enc.get("disk_encrypted"),
        "root_login_permitted": ssh.get("root_login_permitted"),
        "password_auth_permitted": ssh.get("password_auth_permitted"),
        "mac_tool": mac.get("mac_tool"),
        "mac_enabled": mac.get("mac_enabled"),
    }
    ok = send_data("telemetry/security-status", payload)
    print(f"[agent] security-status → {'ok' if ok else 'FAILED'}", flush=True)


def collect_os_info():
    """OS distro/kernel info — once daily."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "os_info": system_profile.get_os_info(),
    }
    ok = send_data("telemetry/os-info", payload)
    print(f"[agent] os-info → {'ok' if ok else 'FAILED'}", flush=True)


def collect_hardware_info():
    """Hardware specs — once daily."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "hardware_info": system_profile.get_hardware_info(),
    }
    ok = send_data("telemetry/hardware-info", payload)
    print(f"[agent] hardware-info → {'ok' if ok else 'FAILED'}", flush=True)


def collect_installed_packages():
    """Full installed package list — once daily."""
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "installed_packages": system_profile.get_installed_packages(),
    }
    ok = send_data("telemetry/installed-packages", payload)
    print(f"[agent] installed-packages → {'ok' if ok else 'FAILED'}", flush=True)


# ── Registration helpers ──────────────────────────────────────────────────────

def _prompt_for_enrollment_token():
    print("", flush=True)
    print("=" * 55, flush=True)
    print("  This node is not registered with an Argus server.", flush=True)
    print("  Generate a token on the server with:", flush=True)
    print("    cd argus-backend && python generate_token.py", flush=True)
    print("=" * 55, flush=True)

    while True:
        try:
            token = input("  Paste enrollment token: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[registration] No token provided. Exiting.", flush=True)
            sys.exit(1)
        if token:
            return token
        print("  Token cannot be empty. Try again.", flush=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Argus agent starting up...", flush=True)

    # Step 1: Registration
    if not is_registered():
        print("Not registered. Checking for enrollment token...", flush=True)
        import os
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv("ARGUS_ENROLLMENT_TOKEN", "").strip()
        if not token or token == "replace-with-real-token-later":
            token = _prompt_for_enrollment_token()

        machine_id = system_profile.get_machine_id()
        hostname = system_profile.get_hostname()
        if not register_node(machine_id, hostname, enrollment_token=token):
            print("Registration failed. Exiting.", flush=True)
            sys.exit(1)

    credentials = load_credentials()
    print(f"[agent] Operating as node_id={credentials['node_id']}", flush=True)

    # Step 2: Restore scheduled enforcement rules (firewall windows etc.)
    restore_scheduled_rules()

    # Step 3: One-time startup collection
    collect_startup()

    # Step 4: Command poll loop in background thread (every 10 sec)
    poll_thread = threading.Thread(target=run_poll_loop, daemon=True)
    poll_thread.start()
    print("[agent] Command poll loop started (background thread).", flush=True)

    # Step 5: Wire up per-function scheduler
    # 1-minute functions
    schedule.every(1).minutes.do(collect_cpu)
    schedule.every(1).minutes.do(collect_processes)
    schedule.every(1).minutes.do(collect_browser_history)

    # 5-minute functions
    schedule.every(5).minutes.do(collect_disk)
    schedule.every(5).minutes.do(collect_ram)
    schedule.every(5).minutes.do(collect_network_io)
    schedule.every(5).minutes.do(collect_active_connections)
    schedule.every(5).minutes.do(collect_system_logs)
    schedule.every(5).minutes.do(collect_auth_events)

    # 30-minute functions
    schedule.every(30).minutes.do(collect_network_interfaces)
    schedule.every(30).minutes.do(collect_dns_servers)
    schedule.every(30).minutes.do(collect_routing_table)
    schedule.every(30).minutes.do(collect_security_status)

    # Daily functions
    schedule.every().day.at("03:00").do(collect_os_info)
    schedule.every().day.at("03:01").do(collect_hardware_info)
    schedule.every().day.at("03:02").do(collect_installed_packages)

    # Retry queue for failed sends
    schedule.every(2).minutes.do(retry_queued_sends)

    print("[agent] Scheduler configured. Entering main loop.", flush=True)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Agent shutting down.", flush=True)
        sys.exit(0)
