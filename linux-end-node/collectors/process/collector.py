import psutil
import time
import subprocess

def get_running_processes():
    """
    Returns a snapshot of all currently running processes with the
    fields needed for rule enforcement and ML baselining. Skips
    processes that disappear or are inaccessible mid-scan (normal
    behavior — processes start/stop constantly).
    """
    processes = []

    # psutil.process_iter lets us request specific fields up front,
    # which is more efficient than creating a Process object per PID
    # and querying each field separately.
    for proc in psutil.process_iter([
        "pid", "name", "username", "cmdline",
        "status", "create_time"
    ]):
        try:
            info = proc.info  # the fields we requested above, as a dict

            processes.append({
                "pid": info["pid"],
                "name": info["name"],
                "username": info["username"],
                "cmdline": " ".join(info["cmdline"]) if info["cmdline"] else "",
                "status": info["status"],
                "create_time": info["create_time"],
                "cpu_percent": proc.cpu_percent(interval=None),
                "memory_percent": round(proc.memory_percent(), 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # The process ended, or we don't have permission to read it,
            # or it's a zombie with incomplete info. Skip it and move on
            # rather than crashing the whole collection.
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

if __name__ == "__main__":
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