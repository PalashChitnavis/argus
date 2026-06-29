import psutil

def get_disk_usage():
    """
    Collects current disk usage for the root partition. Meant to be
    called frequently (e.g., every few minutes) so the central server
    can build a time series and detect unusual spikes/drops — like a
    large file being written then quickly deleted.
    """
    disk = psutil.disk_usage("/")

    return {
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        "disk_percent_used": disk.percent,
    }

def get_cpu_usage():
    """
    Collects current CPU load as a percentage. Meant to be polled
    frequently so the server can build a time series and catch
    sustained spikes (e.g., a cryptominer running in the background).
    """
    cpu_percent = psutil.cpu_percent(interval=1)

    return {
        "cpu_percent_used": cpu_percent,
    }

def get_ram_usage():
    """
    Collects current RAM usage. Used to build a time series so the
    server can detect memory leaks or unusual spikes over time.
    """
    ram = psutil.virtual_memory()

    return {
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_available_gb": round(ram.available / (1024 ** 3), 2),
        "ram_percent_used": ram.percent,
    }

def get_network_io():
    """
    Collects cumulative network bytes sent/received across all
    interfaces combined, since system boot. Meant to be polled
    frequently — like disk and CPU usage — so the server can compare
    successive readings and calculate throughput rate, catching
    unusual spikes (e.g., a large, fast outbound transfer).
    """
    net_io = psutil.net_io_counters()

    return {
        "bytes_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 2),
        "bytes_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 2),
    }

if __name__ == "__main__":
    print("Disk Usage:", get_disk_usage())
    print("CPU Usage:", get_cpu_usage())
    print("RAM Usage:", get_ram_usage())
    print("Network I/O:", get_network_io())