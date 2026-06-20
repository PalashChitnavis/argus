import subprocess
import json

def get_firewall_status():
    """
    Checks whether UFW (Ubuntu's firewall) is active. Returns a
    simple status the server can check against a "firewall must be
    enabled" policy rule.
    """
    try:
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout.strip()

        if output.startswith("Status: active"):
            firewall_active = True
        elif output.startswith("Status: inactive"):
            firewall_active = False
        else:
            firewall_active = None  # unexpected output format

        return {
            "firewall_tool": "ufw",
            "firewall_active": firewall_active,
        }

    except FileNotFoundError:
        # ufw isn't installed on this system at all
        return {
            "firewall_tool": None,
            "firewall_active": None,
        }
    except subprocess.CalledProcessError:
        # ufw exists but the command failed (e.g., needs root)
        return {
            "firewall_tool": "ufw",
            "firewall_active": None,
        }

def get_disk_encryption_status():
    """
    Checks whether any block device on this system uses LUKS disk
    encryption. Walks the lsblk device tree (devices can have nested
    children, e.g. a partition containing a LUKS container) looking
    for any device with filesystem type 'crypto_LUKS'.
    """
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,FSTYPE,MOUNTPOINT", "-J"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"disk_encrypted": None}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"disk_encrypted": None}

    def device_tree_has_luks(devices):
        """
        Recursively checks a list of block devices (and their nested
        children, if any) for a LUKS-encrypted filesystem type.
        """
        for device in devices:
            if device.get("fstype") == "crypto_LUKS":
                return True

            children = device.get("children")
            if children and device_tree_has_luks(children):
                return True

        return False

    top_level_devices = data.get("blockdevices", [])
    is_encrypted = device_tree_has_luks(top_level_devices)

    return {"disk_encrypted": is_encrypted}

def get_ssh_config_status():
    """
    Checks key SSH daemon security settings: whether root login and
    password authentication are permitted. Returns None for a setting
    if it's not explicitly configured (commented out or absent),
    since that means "using the system default," not a clear yes/no.
    """
    settings = {
        "root_login_permitted": None,
        "password_auth_permitted": None,
    }

    try:
        with open("/etc/ssh/sshd_config", "r") as f:
            for line in f:
                line = line.strip()

                # Skip blank lines and fully commented-out lines
                if not line or line.startswith("#"):
                    continue

                if line.startswith("PermitRootLogin"):
                    value = line.split()[1].lower()
                    settings["root_login_permitted"] = (value == "yes")

                elif line.startswith("PasswordAuthentication"):
                    value = line.split()[1].lower()
                    settings["password_auth_permitted"] = (value == "yes")

    except (FileNotFoundError, PermissionError):
        pass  # leave both settings as None — couldn't read the file

    return settings

def get_mac_status():
    """
    Checks whether AppArmor (Ubuntu/Debian's Mandatory Access Control
    system) is loaded and enforcing profiles. Returns None if
    AppArmor isn't present on this system (e.g., a non-Debian distro
    that might use SELinux instead).
    """
    try:
        result = subprocess.run(
            ["aa-status", "--enabled"],
            capture_output=True,
            text=True,
        )
        # aa-status --enabled returns exit code 0 if AppArmor is
        # enabled, and a non-zero code if it's disabled. Unlike our
        # other subprocess calls, we deliberately don't use
        # check=True here, because a non-zero exit code is itself a
        # normal, expected outcome (means "disabled") - not an error
        # we want to throw an exception for.
        is_enabled = (result.returncode == 0)

        return {
            "mac_tool": "apparmor",
            "mac_enabled": is_enabled,
        }

    except FileNotFoundError:
        return {
            "mac_tool": None,
            "mac_enabled": None,
        }
    
if __name__ == "__main__":
    print("Firewall Status:", get_firewall_status())
    print("Disk Encryption Status:", get_disk_encryption_status())
    print("SSH Config Status:", get_ssh_config_status())
    print("MAC Status:", get_mac_status())