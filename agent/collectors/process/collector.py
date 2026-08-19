import psutil
import time
import subprocess

def get_running_processes():
    processes = []
    now = time.time()

    procs = list(psutil.process_iter([
        "pid", "name", "username", "cmdline",
        "status", "create_time"
    ]))

    # Prime: first call always returns 0.0, so throw it away
    for proc in procs:
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Give the OS time to accumulate CPU ticks between the two samples
    time.sleep(0.5)

    for proc in procs:
        try:
            info = proc.info
            create_time = info["create_time"]
            runtime_seconds = int(now - create_time) if create_time else None

            processes.append({
                "pid": info["pid"],
                "name": info["name"],
                "username": info["username"],
                "cmdline": " ".join(info["cmdline"]) if info["cmdline"] else "",
                "status": info["status"],
                "create_time": create_time,
                "runtime_seconds": runtime_seconds,
                "cpu_percent": proc.cpu_percent(interval=None),  # now real
                "memory_percent": round(proc.memory_percent(), 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return processes

def diff_process_snapshots(old_snapshot, new_snapshot):
    """
    Compares two process snapshots and returns processes that are
    present in new_snapshot but not in old_snapshot — i.e., processes
    that started in between the two collection times.

    Uses (pid, create_time) as the unique identity for a process
    instance, since PIDs can be reused by the OS over time.
    """
    # Build a set of (pid, create_time) tuples from the old snapshot
    # for fast lookup. A set gives us O(1) membership checks instead
    # of looping through old_snapshot for every item in new_snapshot.
    old_identities = {
        (proc["pid"], proc["create_time"]) for proc in old_snapshot
    }

    new_processes = []
    for proc in new_snapshot:
        identity = (proc["pid"], proc["create_time"])
        if identity not in old_identities:
            new_processes.append(proc)

    return new_processes

def get_process_tree_info():
    """
    Returns each running process along with its parent process's PID
    and name. This lets the server detect unusual parent-child
    relationships (e.g., a browser spawning a shell) that a simple
    process list can't reveal.
    """
    tree_info = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = proc.info["pid"]
            name = proc.info["name"]

            parent = proc.parent()  # returns a Process object, or None

            if parent is not None:
                parent_pid = parent.pid
                parent_name = parent.name()
            else:
                # No parent means this is likely PID 1 (init) or a
                # kernel-level process with no traditional parent.
                parent_pid = None
                parent_name = None

            tree_info.append({
                "pid": pid,
                "name": name,
                "parent_pid": parent_pid,
                "parent_name": parent_name,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return tree_info

def get_per_app_connections():
    """
    Aggregates active network connections by process name, giving
    a count of how many connections each app currently has open.
    This is our proxy for "which app is using the network most"
    since Linux doesn't expose per-process bytes natively without
    packet capture tools.

    Returns a list of dicts sorted by connection count descending
    so the most network-active apps appear first.
    """
    import psutil
    from collections import defaultdict

    connection_counts = defaultdict(int)
    connection_details = defaultdict(set)

    for conn in psutil.net_connections(kind="inet"):
        if conn.pid is None:
            continue
        try:
            proc_name = psutil.Process(conn.pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        connection_counts[proc_name] += 1

        # Track unique remote IPs this app is talking to
        if conn.raddr:
            connection_details[proc_name].add(conn.raddr.ip)

    result = []
    for app_name, count in connection_counts.items():
        result.append({
            "app_name": app_name,
            "connection_count": count,
            "unique_remote_ips": len(connection_details[app_name]),
        })

    # Sort by connection count, most active first
    result.sort(key=lambda x: x["connection_count"], reverse=True)
    return result

if __name__ == "__main__":
    import time

    print("Taking first snapshot...")
    snapshot_1 = get_running_processes()

    print("Launching a test process and waiting 2 seconds...")
    subprocess.Popen(["sleep", "5"])
    time.sleep(2)

    print("Taking second snapshot...")
    snapshot_2 = get_running_processes()

    new_procs = diff_process_snapshots(snapshot_1, snapshot_2)
    print(f"\nNew processes detected: {len(new_procs)}")
    for p in new_procs:
        print(p)

    print("\nProcess tree (first 5):")
    tree = get_process_tree_info()
    for entry in tree[:5]:
        print(entry)

    print("\nPer-app connection counts:")
    app_conns = get_per_app_connections()
    for entry in app_conns[:10]:
        print(entry)

    print("\nSample process with runtime:")
    if snapshot_2:
        print(snapshot_2[0])