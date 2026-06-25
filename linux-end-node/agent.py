import time
import sys
import threading
import schedule

from collectors.system_profile import collector as system_profile
from collectors.resource_usage import collector as resource_usage
from collectors.process import collector as process
from collectors.network import collector as network
from collectors.security import collector as security
from collectors.logs import collector as logs
from transport.sender import send_data, retry_queued_sends
from registration.register import is_registered, load_credentials, register_node
from command_poll.poller import run_poll_loop
from enforcement.scheduler import restore_scheduled_rules

last_process_snapshot = []


def run_startup_collection():
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
    print(f"Initial process snapshot: {len(last_process_snapshot)} processes", flush=True)


def run_one_minute_collection():
    global last_process_snapshot

    current_snapshot = process.get_running_processes()
    new_processes = process.diff_process_snapshots(last_process_snapshot, current_snapshot)

    payload = {
        "machine_id": system_profile.get_machine_id(),
        "cpu_usage": resource_usage.get_cpu_usage(),
        "new_processes": new_processes,
    }

    success = send_data("one-minute-data", payload)
    print(f"1-min data send {'succeeded' if success else 'failed'}", flush=True)

    last_process_snapshot = current_snapshot


def run_five_minute_collection():
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "disk_usage": resource_usage.get_disk_usage(),
        "ram_usage": resource_usage.get_ram_usage(),
        "network_io": resource_usage.get_network_io(),
        "connections": network.get_active_connections(),
        "recent_logs": logs.get_recent_logs(minutes_back=5),
        "auth_events": logs.get_auth_events(minutes_back=5),
    }

    success = send_data("five-minute-data", payload)
    print(f"5-min data send {'succeeded' if success else 'failed'}", flush=True)


def run_thirty_minute_collection():
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "interfaces": network.get_network_interfaces(),
        "dns_servers": network.get_dns_servers(),
        "routing_table": network.get_routing_table(),
        "firewall_status": security.get_firewall_status(),
        "disk_encryption": security.get_disk_encryption_status(),
        "ssh_config": security.get_ssh_config_status(),
        "mac_status": security.get_mac_status(),
    }

    success = send_data("thirty-minute-data", payload)
    print(f"30-min data send {'succeeded' if success else 'failed'}", flush=True)


def run_daily_collection():
    payload = {
        "machine_id": system_profile.get_machine_id(),
        "os_info": system_profile.get_os_info(),
        "hardware_info": system_profile.get_hardware_info(),
        "installed_packages": system_profile.get_installed_packages(),
    }

    success = send_data("daily-data", payload)
    print(f"Daily data send {'succeeded' if success else 'failed'}", flush=True)


def main():
    print("Argus agent starting up...", flush=True)

    # --- Step 1: Registration check ---
    if not is_registered():
        print("Not registered. Attempting registration...", flush=True)
        machine_id = system_profile.get_machine_id()
        hostname = system_profile.get_hostname()
        success = register_node(machine_id, hostname)
        if not success:
            print("Registration failed. Exiting.", flush=True)
            sys.exit(1)

    credentials = load_credentials()
    print(f"Operating as node_id={credentials['node_id']}", flush=True)

    # --- Step 2: Restore any scheduled enforcement rules ---
    restore_scheduled_rules()

    # --- Step 3: Startup data collection ---
    run_startup_collection()

    # --- Step 4: Start command poll loop in background thread ---
    poll_thread = threading.Thread(target=run_poll_loop, daemon=True)
    poll_thread.start()
    print("Command poll loop started (background thread).", flush=True)

    # --- Step 5: Wire up the scheduler ---
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
        print("Agent shutting down.", flush=True)
        sys.exit(0)