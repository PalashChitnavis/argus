import psutil

def get_network_interfaces():
    """
    Returns a list of network interfaces on this machine along with
    their IP and MAC addresses. Useful for detecting unexpected or
    unauthorized interfaces (e.g., a rogue USB network adapter).
    """
    interfaces = []

    all_addrs = psutil.net_if_addrs()  # dict: {interface_name: [address_objects]}

    for interface_name, addr_list in all_addrs.items():
        interface_info = {
            "interface_name": interface_name,
            "ipv4": None,
            "ipv6": None,
            "mac_address": None,
        }

        for addr in addr_list:
            # psutil uses socket address family constants to distinguish
            # IPv4, IPv6, and MAC (link-layer) addresses within the same list
            if addr.family.name == "AF_INET":
                interface_info["ipv4"] = addr.address
            elif addr.family.name == "AF_INET6":
                interface_info["ipv6"] = addr.address
            elif addr.family.name == "AF_PACKET":
                interface_info["mac_address"] = addr.address

        interfaces.append(interface_info)

    return interfaces

def get_active_connections():
    """
    Returns all active network connections (TCP/UDP) along with the
    process that owns each one. This is the primary data source for
    detecting suspicious outbound connections, unexpected listening
    services, and beaconing behavior.
    """
    connections = []

    # kind="inet" filters to IPv4/IPv6 TCP and UDP connections only,
    # excluding Unix domain sockets (local inter-process communication,
    # not network traffic, so not relevant here)
    for conn in psutil.net_connections(kind="inet"):

        # laddr/raddr are named tuples like (ip, port). raddr can be
        # empty if there's no remote endpoint yet (e.g., a listening
        # socket waiting for incoming connections).
        local_ip = conn.laddr.ip if conn.laddr else None
        local_port = conn.laddr.port if conn.laddr else None
        remote_ip = conn.raddr.ip if conn.raddr else None
        remote_port = conn.raddr.port if conn.raddr else None

        process_name = None
        if conn.pid is not None:
            try:
                process_name = psutil.Process(conn.pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = None

        connections.append({
            "local_ip": local_ip,
            "local_port": local_port,
            "remote_ip": remote_ip,
            "remote_port": remote_port,
            "status": conn.status,
            "pid": conn.pid,
            "process_name": process_name,
        })

    return connections

def get_dns_servers():
    """
    Returns the DNS servers this machine is configured to use, read
    from /etc/resolv.conf. Useful for detecting unauthorized DNS
    changes — a common indicator of network tampering or MITM setup.
    """
    dns_servers = []

    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    # line looks like: "nameserver 127.0.0.53"
                    parts = line.split()
                    if len(parts) >= 2:
                        dns_servers.append(parts[1])
    except FileNotFoundError:
        pass

    return dns_servers
if __name__ == "__main__":
    print("Network Interfaces:")
    for iface in get_network_interfaces():
        print(iface)

    print("\nActive Connections:")
    connections = get_active_connections()
    print(f"Total connections: {len(connections)}")
    for conn in connections[:10]:
        print(conn)

    print("\nDNS Servers:", get_dns_servers())