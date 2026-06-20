import time
import sys
import schedule

from collectors.system_profile import collector as system_profile
from collectors.resource_usage import collector as resource_usage
from collectors.process import collector as process
from collectors.network import collector as network
from collectors.security import collector as security
from collectors.logs import collector as logs
from transport.sender import send_data, retry_queued_sends

# Keeps the most recent process snapshot in memory, so each new
# snapshot can be diffed against it to detect newly started processes.
last_process_snapshot = []


def run_startup_collection():
    """
    Runs once when the agent starts. Sends static identity/profile
    data, plus takes the very first process snapshot so later diffs
    have something to compare against.
    """
    global last_process_snapshot

    print("Running startup collection...", flush=True)

    payload = {
        "machine_id": system_profile.get_machine_id(),
        "hostname": system_profile.get_hostname(),
        "os_info": system_profile.get_os_info(),
        "hardware_info": system_profile.get_hardware_info(),
        "installed_packages": system_profile.get_installed_packages(),
    }

    success = send_data("startup-data", payload)
    print(f"Startup data send {'succeeded' if success else 'failed'}", flush=True)

    last_process_snapshot = process.get_running_processes()
    print(f"Initial process snapshot taken: {len(last_process_snapshot)} processes", flush=True)

def run_daily_collection():
    """Re-checks mostly-static data that can occasionally drift."""
    machine_id = system_profile.get_machine_id()

    payload = {
        "machine_id": machine_id,
        "os_info": system_profile.get_os_info(),
        "hardware_info": system_profile.get_hardware_info(),
        "installed_packages": system_profile.get_installed_packages(),
    }

    success = send_data("daily-data", payload)
    print(f"Daily data send {'succeeded' if success else 'failed'}", flush=True)


def run_one_minute_collection():
    """High-frequency tier: CPU usage and process diffing."""
    global last_process_snapshot

    machine_id = system_profile.get_machine_id()
    cpu_usage = resource_usage.get_cpu_usage()

    current_snapshot = process.get_running_processes()
    new_processes = process.diff_process_snapshots(last_process_snapshot, current_snapshot)

    payload = {
        "machine_id": machine_id,
        "cpu_usage": cpu_usage,
        "new_processes": new_processes,
    }

    success = send_data("one-minute-data", payload)
    print(f"1-minute data send {'succeeded' if success else 'failed'}", flush=True)

    last_process_snapshot = current_snapshot


def run_five_minute_collection():
    """Mid-frequency tier: resource usage, connections, logs."""
    print("Running 5-minute collection...", flush=True)

    machine_id = system_profile.get_machine_id()

    payload = {
        "machine_id": machine_id,
        "disk_usage": resource_usage.get_disk_usage(),
        "ram_usage": resource_usage.get_ram_usage(),
        "network_io": resource_usage.get_network_io(),
        "connections": network.get_active_connections(),
        "recent_logs": logs.get_recent_logs(minutes_back=5),
        "auth_events": logs.get_auth_events(minutes_back=5),
    }

    success = send_data("five-minute-data", payload)
    print(f"5-minute data send {'succeeded' if success else 'failed'}", flush=True)


def run_thirty_minute_collection():
    """Low-frequency tier: network topology and security posture."""
    machine_id = system_profile.get_machine_id()

    payload = {
        "machine_id": machine_id,
        "interfaces": network.get_network_interfaces(),
        "dns_servers": network.get_dns_servers(),
        "routing_table": network.get_routing_table(),
        "firewall_status": security.get_firewall_status(),
        "disk_encryption": security.get_disk_encryption_status(),
        "ssh_config": security.get_ssh_config_status(),
        "mac_status": security.get_mac_status(),
    }

    success = send_data("thirty-minute-data", payload)
    print(f"30-minute data send {'succeeded' if success else 'failed'}", flush=True)


def main():
    print("Argus Linux end node agent starting up...", flush=True)

    run_startup_collection()

    schedule.every(1).minutes.do(run_one_minute_collection)
    schedule.every(5).minutes.do(run_five_minute_collection)
    schedule.every(30).minutes.do(run_thirty_minute_collection)
    schedule.every().day.at("03:00").do(run_daily_collection)

    schedule.every(2).minutes.do(retry_queued_sends)

    print("Scheduler configured. Entering main loop.", flush=True)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Agent shutting down (received interrupt).", flush=True)
        sys.exit(0)