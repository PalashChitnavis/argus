import subprocess
import psutil


def _run_tc(args):
    """Internal helper — runs a tc (traffic control) command."""
    try:
        result = subprocess.run(
            ["tc"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "tc not found — install iproute2"


def _get_active_interface():
    """
    Returns the name of the first non-loopback interface that has
    an IPv4 address — i.e., the one actually carrying traffic.
    Used as a fallback when no interface is explicitly specified.
    """
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for iface, addr_list in addrs.items():
        if iface == "lo":
            continue
        if not stats.get(iface, None) or not stats[iface].isup:
            continue
        for addr in addr_list:
            if addr.family.name == "AF_INET":
                return iface

    return None


def set_bandwidth_limit(rate_mbit, interface=None):
    """
    Limits outbound bandwidth on the given interface using tc (traffic
    control). rate_mbit is in Megabits per second (e.g. 1 = 1 Mbit/s).
    If no interface is specified, uses the active one automatically.

    Replaces any existing limit on that interface (safe to call
    multiple times — idempotent).
    """
    if interface is None:
        interface = _get_active_interface()
    if interface is None:
        return {"success": False, "output": "Could not detect active network interface"}

    # Remove any existing qdisc first — if none exists tc returns an
    # error which we can safely ignore, so we don't use check=True here
    subprocess.run(
        ["tc", "qdisc", "del", "dev", interface, "root"],
        capture_output=True,
    )

    # tbf = Token Bucket Filter — the standard tc algorithm for rate
    # limiting. burst = maximum bytes sent at once before limiting
    # kicks in. latency = max time a packet can sit in the queue.
    rate_str = f"{rate_mbit}mbit"
    success, output = _run_tc([
        "qdisc", "add", "dev", interface, "root",
        "tbf", "rate", rate_str,
        "burst", "32kbit",
        "latency", "400ms",
    ])

    return {
        "success": success,
        "output": output,
        "interface": interface,
        "rate_mbit": rate_mbit,
    }


def remove_bandwidth_limit(interface=None):
    """
    Removes any tc bandwidth limit on the given interface,
    restoring full speed.
    """
    if interface is None:
        interface = _get_active_interface()
    if interface is None:
        return {"success": False, "output": "Could not detect active network interface"}

    success, output = _run_tc([
        "qdisc", "del", "dev", interface, "root"
    ])

    return {"success": success, "output": output, "interface": interface}


def get_bandwidth_limit(interface=None):
    """
    Returns the current tc qdisc config for the interface — lets us
    see whether a limit is currently applied and what it is.
    """
    if interface is None:
        interface = _get_active_interface()
    if interface is None:
        return {"interface": None, "limited": False}

    try:
        result = subprocess.run(
            ["tc", "qdisc", "show", "dev", interface],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()

        # "noqueue" or "fq_codel" = default/no limit applied by us.
        # "tbf" = our Token Bucket Filter limit is active.
        limited = "tbf" in output

        return {
            "interface": interface,
            "limited": limited,
            "tc_output": output,
        }
    except subprocess.CalledProcessError:
        return {"interface": interface, "limited": False}


if __name__ == "__main__":
    print("=== Bandwidth Enforcement Tests ===\n")

    print("1. Checking current state (no limit should be active)...")
    print(get_bandwidth_limit())

    print("\n2. Applying 1 Mbit/s limit...")
    print(set_bandwidth_limit(1))

    print("\n3. Checking state again (tbf should now show up)...")
    print(get_bandwidth_limit())

    print("\n4. Replacing with a 5 Mbit/s limit (idempotency check)...")
    print(set_bandwidth_limit(5))

    print("\n5. Removing the limit entirely...")
    print(remove_bandwidth_limit())

    print("\n6. Final state check (should show no tbf)...")
    print(get_bandwidth_limit())