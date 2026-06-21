import platform
import socket
import subprocess
import psutil

def get_os_info():
    """
    Collects OS distribution name, version, kernel version, and architecture.
    Reads /etc/os-release (a standard file on all modern Linux distros)
    plus Python's built-in platform module for kernel/architecture info.
    """
    wanted_fields = {
        "NAME": "distro_name",
        "ID": "distro_id",
        "VERSION_ID": "distro_version",
        "VERSION_CODENAME": "distro_codename",
    }

    os_info = {}

    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                line = line.strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in wanted_fields:
                    clean_key = wanted_fields[key]
                    os_info[clean_key] = value.strip('"')
    except FileNotFoundError:
        os_info["distro_name"] = "Unknown"

    os_info["kernel_version"] = platform.release()
    os_info["architecture"] = platform.machine()

    return os_info

def get_hostname():
    """
    Returns the hostname of this machine — how it identifies itself
    on the network.
    """
    return socket.gethostname()

def get_machine_id():
    """
    Returns the unique, persistent machine ID for this Linux system.
    Unlike hostname (which can be changed by a user), this ID stays
    constant for the life of the OS install — making it a reliable
    way for the central server to identify this specific device.
    """
    try:
        with open("/etc/machine-id", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    
def get_hardware_info():
    """
    Collects CPU, RAM, and disk specs. Returns static-ish specs (not live
    usage — that belongs in a separate live-monitoring collector later).
    """
    hardware_info = {}

    # CPU
    hardware_info["cpu_cores_physical"] = psutil.cpu_count(logical=False)
    hardware_info["cpu_cores_logical"] = psutil.cpu_count(logical=True)

    # RAM (psutil returns bytes, so we convert to GB for readability)
    total_ram_bytes = psutil.virtual_memory().total
    hardware_info["ram_total_gb"] = round(total_ram_bytes / (1024 ** 3), 2)

    # Disk (root partition only, for now)
    disk_usage = psutil.disk_usage("/")
    hardware_info["disk_total_gb"] = round(disk_usage.total / (1024 ** 3), 2)

    return hardware_info

def get_installed_packages():
    """
    Returns a list of installed package names (not versions, not
    descriptions) using dpkg. Kept deliberately minimal — full package
    metadata is noisy; just the name is enough to detect banned
    software or meaningful changes between snapshots.
    """
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\n"],
            capture_output=True,
            text=True,
            check=True,
        )
        packages = result.stdout.strip().split("\n")
        return packages
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    
if __name__ == "__main__":
    print("OS Info:", get_os_info())
    print("Hostname:", get_hostname())
    print("Machine ID:", get_machine_id())
    print("Hardware Info:", get_hardware_info())
    packages = get_installed_packages()
    print(f"Installed Packages ({len(packages)} total):", packages[:10], "...")