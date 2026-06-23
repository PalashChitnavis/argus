import subprocess
import pwd


def _run_iptables(args):
    """Internal helper — runs an iptables command."""
    try:
        result = subprocess.run(
            ["iptables"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "iptables not found"


def _resolve_uid(username):
    """
    Converts a Linux username to its numeric UID.
    iptables --uid-owner requires a UID, not a username.
    Returns None if the user doesn't exist.
    """
    try:
        return pwd.getpwnam(username).pw_uid
    except KeyError:
        return None


def block_user_network(username, port=None, protocol="tcp"):
    """
    Blocks outbound network access for a specific Linux user.
    If port is given, only blocks that specific port.
    If port is None, blocks ALL outbound traffic for that user.
    """
    uid = _resolve_uid(username)
    if uid is None:
        return {"success": False, "output": f"User '{username}' not found on this system"}

    # Base iptables rule targeting this user's UID on OUTPUT chain
    args = [
        "-A", "OUTPUT",
        "-m", "owner", "--uid-owner", str(uid),
    ]

    if port is not None:
        args += ["-p", protocol, "--dport", str(port)]

    args += ["-j", "DROP"]

    success, output = _run_iptables(args)
    return {
        "success": success,
        "output": output,
        "username": username,
        "uid": uid,
        "port": port,
    }


def unblock_user_network(username, port=None, protocol="tcp"):
    """
    Removes an iptables block for a specific user.
    Uses -D (delete) instead of -A (append) — same rule, opposite operation.
    """
    uid = _resolve_uid(username)
    if uid is None:
        return {"success": False, "output": f"User '{username}' not found on this system"}

    args = [
        "-D", "OUTPUT",
        "-m", "owner", "--uid-owner", str(uid),
    ]

    if port is not None:
        args += ["-p", protocol, "--dport", str(port)]

    args += ["-j", "DROP"]

    success, output = _run_iptables(args)
    return {"success": success, "output": output, "username": username}


def list_user_blocks():
    """
    Lists all argus-managed OUTPUT DROP rules currently in iptables.
    """
    try:
        result = subprocess.run(
            ["iptables", "-L", "OUTPUT", "-n", "--line-numbers"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Filter to just DROP rules — those are ours
        rules = []
        for line in result.stdout.splitlines():
            if "DROP" in line:
                rules.append(line.strip())
        return rules
    except subprocess.CalledProcessError:
        return []


if __name__ == "__main__":
    print("=== IPTables Per-User Enforcement Tests ===\n")
    import getpass

    # Use the current non-root user for testing
    current_user = getpass.getuser()
    print(f"Testing with current user context. Active user: palash")

    print("\n1. Listing current OUTPUT DROP rules (should be empty)...")
    print(list_user_blocks())

    print(f"\n2. Blocking port 443 (HTTPS) for user 'palash'...")
    print(block_user_network("palash", port=443))

    print("\n3. Listing rules again (should show our DROP rule)...")
    print(list_user_blocks())

    print("\n4. Unblocking port 443 for 'palash'...")
    print(unblock_user_network("palash", port=443))

    print("\n5. Final rule list (should be empty again)...")
    print(list_user_blocks())