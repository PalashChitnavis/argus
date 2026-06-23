import subprocess


def _run_ufw(args):
    """
    Internal helper — runs a ufw command with the given argument list.
    Returns (success: bool, output: str).
    """
    try:
        result = subprocess.run(
            ["ufw"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "ufw not found on this system"


def enable_firewall():
    """Enables UFW."""
    # --force skips the interactive 'are you sure?' prompt
    success, output = _run_ufw(["--force", "enable"])
    return {"success": success, "output": output}


def disable_firewall():
    """Disables UFW."""
    success, output = _run_ufw(["--force", "disable"])
    return {"success": success, "output": output}


def add_port_rule(action, port, protocol="tcp", direction="in"):
    """
    Adds a UFW rule targeting a port.
    action    : "allow" or "deny"
    port      : integer or string e.g. 22 or "22"
    protocol  : "tcp", "udp", or "any"
    direction : "in" or "out"
    """
    target = f"{port}/{protocol}" if protocol != "any" else str(port)

    if direction == "out":
        args = [action, "out", target]
    else:
        args = [action, target]

    success, output = _run_ufw(args)
    return {"success": success, "output": output}


def add_ip_rule(action, ip, direction="in"):
    """
    Adds a UFW rule targeting an IP address or CIDR range.
    action : "allow" or "deny"
    ip     : e.g. "192.168.1.50" or "10.0.0.0/8"
    """
    if direction == "out":
        args = [action, "out", "to", ip]
    else:
        args = [action, "from", ip]

    success, output = _run_ufw(args)
    return {"success": success, "output": output}


def add_ip_port_rule(action, ip, port, protocol="tcp", direction="in"):
    """
    Adds a UFW rule combining an IP and a port — most precise form.
    e.g. allow from 10.0.0.5 to any port 5432
    """
    target_port = f"{port}/{protocol}" if protocol != "any" else str(port)

    if direction == "out":
        args = [action, "out", "to", ip, "port", str(port), "proto", protocol]
    else:
        args = [action, "from", ip, "to", "any", "port", str(port), "proto", protocol]

    success, output = _run_ufw(args)
    return {"success": success, "output": output}


def delete_rule(rule_number):
    """
    Deletes a UFW rule by its number (from get_firewall_rules() output).
    --force skips the interactive confirmation prompt.
    """
    success, output = _run_ufw(["--force", "delete", str(rule_number)])
    return {"success": success, "output": output}


def reset_firewall():
    """
    Resets UFW to defaults — removes ALL rules. Use carefully.
    """
    success, output = _run_ufw(["--force", "reset"])
    return {"success": success, "output": output}


if __name__ == "__main__":
    import sys

    print("=== Firewall Enforcement Tests ===\n")

    print("1. Enabling firewall...")
    print(enable_firewall())

    print("\n2. Adding allow rule for port 22/tcp (inbound)...")
    print(add_port_rule("allow", 22, "tcp", "in"))

    print("\n3. Adding deny rule for port 8080/tcp (inbound)...")
    print(add_port_rule("deny", 8080, "tcp", "in"))

    print("\n4. Adding deny rule for IP 1.2.3.4...")
    print(add_ip_rule("deny", "1.2.3.4", "in"))

    print("\n5. Adding allow rule for IP+port combo...")
    print(add_ip_port_rule("allow", "10.0.0.5", 5432, "tcp", "in"))

    print("\n6. Checking current rules via ufw status numbered...")
    import subprocess
    result = subprocess.run(["ufw", "status", "numbered"],
                            capture_output=True, text=True)
    print(result.stdout)

    print("\n7. Deleting rule number 1...")
    print(delete_rule(1))

    print("\n8. Disabling firewall...")
    print(disable_firewall())

    print("\nDone. Firewall is back off.")