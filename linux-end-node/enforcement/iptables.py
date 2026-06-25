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
    Returns all argus-managed OUTPUT DROP rules currently in
    iptables as structured dicts, not raw strings. Each dict has
    the line number (for deletion), target (protocol/port), and
    source — making it directly usable by the frontend without
    any further parsing.
    """
    try:
        result = subprocess.run(
            ["iptables", "-L", "OUTPUT", "-n", "--line-numbers"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return []

    rules = []

    for line in result.stdout.splitlines():
        if "DROP" not in line:
            continue

        parts = line.split()

        # iptables -L --line-numbers output columns:
        # num  target  prot  opt  source  destination  [extras]
        # e.g: 1  DROP  tcp  --  0.0.0.0/0  0.0.0.0/0  owner UID match 1000 tcp dpt:443
        if len(parts) < 6:
            continue

        try:
            rule_dict = {
                "line_number": int(parts[0]),
                "target": parts[1],       # DROP
                "protocol": parts[2],     # tcp/udp/all
                "source": parts[4],       # source IP (0.0.0.0/0 = any)
                "destination": parts[5],  # dest IP
                "uid": None,
                "port": None,
            }

            # Parse the extras at the end of the line for UID and port
            # They look like: "owner UID match 1000 tcp dpt:443"
            rest = " ".join(parts[6:])

            # Extract UID
            if "UID match" in rest:
                uid_index = parts.index("match") if "match" in parts else None
                for i, part in enumerate(parts):
                    if part == "match" and i + 1 < len(parts):
                        try:
                            rule_dict["uid"] = int(parts[i + 1])
                        except ValueError:
                            pass

            # Extract destination port (dpt:443)
            for part in parts:
                if part.startswith("dpt:"):
                    try:
                        rule_dict["port"] = int(part.split(":")[1])
                    except (ValueError, IndexError):
                        pass

            # Resolve UID back to username for readability
            if rule_dict["uid"] is not None:
                try:
                    rule_dict["username"] = pwd.getpwuid(rule_dict["uid"]).pw_name
                except KeyError:
                    rule_dict["username"] = str(rule_dict["uid"])
            else:
                rule_dict["username"] = None

            rules.append(rule_dict)

        except (ValueError, IndexError):
            continue

    return rules


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