import re

HOSTS_FILE = "/etc/hosts"
ARGUS_MARKER = "# argus-managed"


def _read_hosts():
    with open(HOSTS_FILE, "r") as f:
        return f.readlines()


def _write_hosts(lines):
    with open(HOSTS_FILE, "w") as f:
        f.writelines(lines)


def block_domain(domain):
    """
    Blocks a domain by redirecting it to 0.0.0.0 in /etc/hosts.
    Adds both bare domain and www. variant.
    Skips if domain is already blocked (idempotent).
    """
    lines = _read_hosts()

    # Check if already blocked — avoid duplicates
    for line in lines:
        if domain in line and ARGUS_MARKER in line:
            return {"success": True, "output": f"{domain} already blocked"}

    # Add both www and bare domain, tagged so we can find/remove
    # them later without touching anything we didn't add
    new_lines = [
        f"0.0.0.0 {domain} {ARGUS_MARKER}\n",
        f"0.0.0.0 www.{domain} {ARGUS_MARKER}\n",
    ]

    _write_hosts(lines + new_lines)
    return {"success": True, "output": f"Blocked {domain} and www.{domain}"}


def unblock_domain(domain):
    """
    Removes an argus-managed block for the given domain.
    Only removes lines that have our marker — never touches
    lines that were in /etc/hosts before argus got here.
    """
    lines = _read_hosts()
    new_lines = [
        line for line in lines
        if not (domain in line and ARGUS_MARKER in line)
    ]

    if len(new_lines) == len(lines):
        return {"success": False, "output": f"{domain} was not blocked by argus"}

    _write_hosts(new_lines)
    return {"success": True, "output": f"Unblocked {domain}"}


def list_blocked_domains():
    """
    Returns all domains currently blocked by argus via /etc/hosts.
    """
    lines = _read_hosts()
    blocked = []

    for line in lines:
        if ARGUS_MARKER in line:
            parts = line.strip().split()
            if len(parts) >= 2:
                domain = parts[1]
                # Skip www. variants — deduplicate to just the root domain
                if not domain.startswith("www."):
                    blocked.append(domain)

    return blocked


def clear_all_blocks():
    """
    Removes ALL argus-managed blocks from /etc/hosts. Used for
    cleanup or factory reset scenarios.
    """
    lines = _read_hosts()
    new_lines = [line for line in lines if ARGUS_MARKER not in line]
    _write_hosts(new_lines)
    removed = len(lines) - len(new_lines)
    return {"success": True, "output": f"Removed {removed} argus-managed lines"}


if __name__ == "__main__":
    print("=== Hosts Enforcement Tests ===\n")

    print("1. Blocking facebook.com...")
    print(block_domain("facebook.com"))

    print("\n2. Blocking youtube.com...")
    print(block_domain("youtube.com"))

    print("\n3. Blocking facebook.com again (idempotency check)...")
    print(block_domain("facebook.com"))

    print("\n4. Listing blocked domains...")
    print(list_blocked_domains())

    print("\n5. Checking /etc/hosts for our entries...")
    import subprocess
    result = subprocess.run(["grep", "argus-managed", "/etc/hosts"],
                            capture_output=True, text=True)
    print(result.stdout)

    print("\n6. Unblocking facebook.com...")
    print(unblock_domain("facebook.com"))

    print("\n7. Listing blocked domains after unblock...")
    print(list_blocked_domains())

    print("\n8. Clearing all remaining blocks...")
    print(clear_all_blocks())

    print("\n9. Final check — should be empty...")
    print(list_blocked_domains())