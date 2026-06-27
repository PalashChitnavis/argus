# Argus API Reference
## Global Environment Configuration
> **Base URL:** http://127.0.0.1:8000

> **Node ID:** 1

> **API Key:** xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU

> **Enrollment Token:** jboxdDtvpHrXquknFvt3Une6KgS2C2vt6gC7EWtv1NI
> 
## 1. Registration
### POST /register
 * **Description:** First-time node registration. Consumes the enrollment token (single use). Returns a node_id and api_key which the agent saves locally to credentials.json.
 * **Caller:** linux-end-node (on first boot)
 * **Authentication:** None (Uses enrollment token in body)
```bash
curl -s -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "enrollment_token": "jboxdDtvpHrXquknFvt3Une6KgS2C2vt6gC7EWtv1NI",
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "hostname": "palash"
  }' | python3 -m json.tool

```
## 2. Telemetry Ingest
> **Note:** All ingest endpoints require **Bearer API Key Authentication** and are called exclusively by the linux-end-node agent on its configured collection schedules.
> 
### POST /startup-data
 * **Description:** Stores OS info, hardware specs, and initial installed packages list. Sent once on agent boot.
```bash
curl -s -X POST http://127.0.0.1:8000/startup-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "os_info": {
      "distro_name": "Ubuntu",
      "distro_version": "24.04",
      "distro_codename": "noble",
      "distro_id": "ubuntu",
      "kernel_version": "6.17.0-35-generic",
      "architecture": "x86_64"
    },
    "hardware_info": {
      "cpu_cores_physical": 4,
      "cpu_cores_logical": 8,
      "ram_total_gb": 15.46,
      "disk_total_gb": 232.64
    },
    "installed_packages": ["vim", "curl", "git", "python3"]
  }' | python3 -m json.tool

```
### POST /one-minute-data
 * **Description:** Stores CPU usage metrics and any new processes that appeared since the last poll interval. Sent every 1 minute.
```bash
curl -s -X POST http://127.0.0.1:8000/one-minute-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "cpu_usage": {
      "cpu_percent_used": 14.3
    },
    "new_processes": [
      {
        "pid": 1234,
        "create_time": 1234567890.0,
        "name": "bash",
        "username": "palash",
        "cmdline": "bash",
        "status": "running",
        "cpu_percent": 0.1,
        "memory_percent": 0.2
      }
    ]
  }' | python3 -m json.tool

```
### POST /five-minute-data
 * **Description:** Stores comprehensive disk, RAM, network I/O, active network connections, recent syslog lines, and authentication events. Sent every 5 minutes.
```bash
curl -s -X POST http://127.0.0.1:8000/five-minute-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "disk_usage": {
      "disk_used_gb": 42.52,
      "disk_free_gb": 178.23,
      "disk_percent_used": 19.3
    },
    "ram_usage": {
      "ram_used_gb": 6.15,
      "ram_available_gb": 9.31,
      "ram_percent_used": 39.8
    },
    "network_io": {
      "bytes_sent_mb": 100.0,
      "bytes_recv_mb": 200.0
    },
    "connections": [
      {
        "local_ip": "127.0.0.1",
        "local_port": 8000,
        "remote_ip": null,
        "remote_port": null,
        "status": "LISTEN",
        "pid": 5972,
        "process_name": "python3"
      }
    ],
    "recent_logs": [
      "Jun 27 21:00:01 palash systemd[1]: Started Daily apt upgrade."
    ],
    "auth_events": [
      "Jun 27 21:00:01 palash sudo: palash : TTY=pts/0 ; USER=root"
    ]
  }' | python3 -m json.tool

```
### POST /thirty-minute-data
 * **Description:** Stores security control postures including firewall status, disk encryption metadata, SSH daemon configuration metrics, AppArmor/SELinux status, system network interfaces, active DNS configurations, and routing tables. Sent every 30 minutes.
```bash
curl -s -X POST http://127.0.0.1:8000/thirty-minute-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "firewall_status": {
      "firewall_tool": "ufw",
      "firewall_active": true
    },
    "disk_encryption": {
      "disk_encrypted": false
    },
    "ssh_config": {
      "root_login_permitted": false,
      "password_auth_permitted": false
    },
    "mac_status": {
      "mac_tool": "apparmor",
      "mac_enabled": true
    },
    "interfaces": [
      {
        "interface_name": "wlp8s0",
        "ipv4": "192.168.1.10",
        "ipv6": null,
        "mac_address": "aa:bb:cc:dd:ee:ff"
      }
    ],
    "dns_servers": ["8.8.8.8", "8.8.4.4"],
    "routing_table": ["default via 192.168.1.1 dev wlp8s0"]
  }' | python3 -m json.tool

```
### POST /daily-data
 * **Description:** Provides a baseline sync storing OS info, hardware specifications, and the complete evaluation list of installed packages. Sent once daily at 03:00.
```bash
curl -s -X POST http://127.0.0.1:8000/daily-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "os_info": {
      "distro_name": "Ubuntu",
      "distro_version": "24.04",
      "distro_codename": "noble",
      "distro_id": "ubuntu",
      "kernel_version": "6.17.0-35-generic",
      "architecture": "x86_64"
    },
    "hardware_info": {
      "cpu_cores_physical": 4,
      "cpu_cores_logical": 8,
      "ram_total_gb": 15.46,
      "disk_total_gb": 232.64
    },
    "installed_packages": ["vim", "curl", "git", "python3"]
  }' | python3 -m json.tool

```
## 3. Telemetry Read
> **Note:** These read endpoints require **No Authentication** and are constructed for intake by frontend client dashboards.
> 
| Endpoint | Description |
|---|---|
| GET /nodes | Lists all registered nodes alongside their aggregated online/offline connectivity status. |
| GET /nodes/{node_id} | Fetches target configuration and runtime heartbeat summary for an explicit node. |
| GET /nodes/{node_id}/status | Obtains target runtime visibility lifecycle parameters (status, last_seen). A node defaults to **online** if it successfully establishes a poll structure within the trailing 30 seconds. |
| GET /nodes/{node_id}/startup-data | Exposes the most recent configuration startup payload metadata snapshot. |
| GET /nodes/{node_id}/startup-data/history | Fetches historical array of startup events. Defaults to 10 records. |
| GET /nodes/{node_id}/one-minute-data | Extracts the latest 1-minute window telemetry (CPU capacity and metrics data tracking). |
| GET /nodes/{node_id}/one-minute-data/history | Historical timeline of 1-minute telemetry blocks. Defaults to 60 records (1 hour). |
| GET /nodes/{node_id}/five-minute-data | Extracts the latest 5-minute snapshot (RAM, disk operations, metrics logs, connection tracking). |
| GET /nodes/{node_id}/five-minute-data/history | Historical dataset of 5-minute telemetry blocks. Defaults to 288 records (24 hours). |
| GET /nodes/{node_id}/thirty-minute-data | Extracts the latest 30-minute interval profile data (firewall configs, interfaces, DNS details). |
| GET /nodes/{node_id}/thirty-minute-data/history | Historical dataset of 30-minute state blocks. Defaults to 48 records (24 hours). |
| GET /nodes/{node_id}/daily-data | Extracts the latest 24-hour evaluation payload (complete operating list environment). |
| GET /nodes/{node_id}/daily-data/history | Historical dataset of comprehensive snapshot layers. Defaults to 30 records. |
| GET /nodes/{node_id}/dashboard | Monolithic consolidation payload querying all target structural metrics layers to feed the primary client user interface layout. |
### Example Telemetry Read Operations
```bash
# Get online status details
curl -s http://127.0.0.1:8000/nodes/1/status | python3 -m json.tool

# Query historical metrics with custom limits
curl -s "http://127.0.0.1:8000/nodes/1/one-minute-data/history?limit=10" | python3 -m json.tool
curl -s "http://127.0.0.1:8000/nodes/1/thirty-minute-data/history?limit=5" | python3 -m json.tool

# Fetch unified frontend dashboard layout payload
curl -s http://127.0.0.1:8000/nodes/1/dashboard | python3 -m json.tool

```
## 4. Firewall Rules CRUD (Admin Management)
> **Note:** Endpoints inside this structure require **No Authentication** and are called directly by the administrative web UI panel application layer. Creating, mutating, or enabling an active policy record dynamically sequences down an underlying enforce configuration mandate payload to the endpoint device. Deactivating or deleting target entities pushes downstream delete_rule commands.
> 
### POST /nodes/{node_id}/firewall-rules
 * **Description:** Registers a firewall orchestration rule entry tracking state inside the central engine datastore and pushes execution state configurations to client queues. Supported values for rule_type: port, ip, ip_port, domain, bandwidth, user_port.
#### Variant: Port Rules
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "port",
    "action": "deny",
    "params": {"port": 8080, "protocol": "tcp", "direction": "in"},
    "enabled": true,
    "description": "Block inbound 8080"
  }' | python3 -m json.tool

```
#### Variant: Network IP Layer Block
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "ip",
    "action": "deny",
    "params": {"ip": "1.2.3.4", "direction": "in"},
    "enabled": true,
    "description": "Block IP 1.2.3.4"
  }' | python3 -m json.tool

```
#### Variant: Targeted IP and Port
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "ip_port",
    "action": "allow",
    "params": {"ip": "10.0.0.5", "port": 5432, "protocol": "tcp", "direction": "in"},
    "enabled": true,
    "description": "Allow 10.0.0.5 to reach postgres"
  }' | python3 -m json.tool

```
#### Variant: Domain Blacklisting (/etc/hosts)
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "domain",
    "action": "block",
    "params": {"domain": "youtube.com"},
    "enabled": true,
    "description": "Block YouTube"
  }' | python3 -m json.tool

```
#### Variant: Bandwidth Shaping Profile Traffic Control (tc)
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "bandwidth",
    "action": "set",
    "params": {"rate_mbit": 1.0, "interface": "wlp8s0"},
    "enabled": true,
    "description": "Limit to 1 Mbps"
  }' | python3 -m json.tool

```
#### Variant: Local User Scoped Restrictions (iptables)
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "user_port",
    "action": "block",
    "params": {"username": "palash", "port": 443, "protocol": "tcp"},
    "enabled": true,
    "description": "Block palash from HTTPS"
  }' | python3 -m json.tool

```
#### Variant: Time-Windowed Scheduled Operations
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "domain",
    "action": "block",
    "params": {"domain": "youtube.com"},
    "schedule": {"start_time": "09:00", "end_time": "17:00"},
    "enabled": true,
    "description": "Block YouTube during work hours"
  }' | python3 -m json.tool

```
### GET /nodes/{node_id}/firewall-rules
 * **Description:** Retrieves all recorded engine management control parameters mapped to a target node.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules | python3 -m json.tool

```
### GET /nodes/{node_id}/firewall-rules/{rule_id}
 * **Description:** Retrieves details for a specific firewall rule entry.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules/1 | python3 -m json.tool

```
### PUT /nodes/{node_id}/firewall-rules/{rule_id}
 * **Description:** Patches an existing control data reference. Mutates explicitly provided fields. Toggling enabled: false shifts execution queue states to send down delete_rule steps. Transitioning back to enabled: true queues a new enforce payload step.
```bash
# Example 1: Disable a policy action item
curl -s -X PUT http://127.0.0.1:8000/nodes/1/firewall-rules/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}' | python3 -m json.tool

# Example 2: Re-enable an existing policy asset 
curl -s -X PUT http://127.0.0.1:8000/nodes/1/firewall-rules/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}' | python3 -m json.tool

```
### DELETE /nodes/{node_id}/firewall-rules/{rule_id}
 * **Description:** Permanently drops tracking details metrics fields from the database layer, returning a 204 No Content code response. If the configuration payload was actively active on the endpoint device (applied=true), an immediate remote agent delete_rule command is issued.
```bash
curl -s -X DELETE http://127.0.0.1:8000/nodes/1/firewall-rules/1

```
### GET /nodes/{node_id}/firewall-status
 * **Description:** Returns an audit summary view detailing firewall status information metrics, tracking active policy states counts, along with an breakdown segmented by rule_type.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-status | python3 -m json.tool

```
## 5. Firewall Rules — Agent Endpoints
> **Note:** Requires explicit **Bearer API Key Authentication**. Accessible only by target linux-end-node edge services execution logic processes.
> 
### GET /nodes/{node_id}/firewall-rules/pending
 * **Description:** Queries historical structural rule states waiting to settle application on client endpoints (applied=false). This services legacy polling-driven configuration operations setups.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules/pending \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  | python3 -m json.tool

```
### POST /nodes/{node_id}/firewall-rules/apply-status
 * **Description:** Receives verification execution reports tracking deployment success or failure constraints back from an agent device to explicitly lock down state flags in the control database registry.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules/apply-status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "rule_id": 1,
    "status": "success"
  }' | python3 -m json.tool

```
## 6. Command Queue — Admin Control
> **Note:** Endpoints within this section require **No Authentication** and are wired for UI interaction routines.
> 
### POST /nodes/{node_id}/commands/enforce
 * **Description:** Queues an enforcement command payload forcing edge infrastructure hosts to establish immediate security configurations execution profiles within a small trailing window (~10s via standard polling loops).
```bash
# Port Block enforcement action execution
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/enforce \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "port",
    "action": "deny",
    "params": {"port": 9090, "protocol": "tcp", "direction": "in"}
  }' | python3 -m json.tool

# Core Routing IP isolation step execution
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/enforce \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "ip",
    "action": "deny",
    "params": {"ip": "1.2.3.4", "direction": "in"}
  }' | python3 -m json.tool

```
### POST /nodes/{node_id}/commands/delete-rule
 * **Description:** Issues a command payload instructing remote nodes to tear down an explicitly defined localized security rule structure.
```bash
# Delete UFW structural tracking instance by known index identifier 
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/delete-rule \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "firewall",
    "rule_number": 1
  }' | python3 -m json.tool

# Revoke a local domain blacklisting configuration override
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/delete-rule \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "domain",
    "domain": "youtube.com"
  }' | python3 -m json.tool

```
### POST /nodes/{node_id}/commands/refresh
 * **Description:** Forces an agent runtime application logic system to instantly re-execute collection steps against a targeted metric tracker domain asset. Output returns inside ~10s on the command context execution path route.
 * **Collector Options:** network_interfaces, active_connections, dns_servers, routing_table, disk_usage, ram_usage, cpu_usage, network_io, running_processes, firewall_status, firewall_rules, all_rules.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/refresh \
  -H "Content-Type: application/json" \
  -d '{"collector": "active_connections"}' | python3 -m json.tool

```
### POST /nodes/{node_id}/commands/get-rules
 * **Description:** Instructs the remote agent tracking instance to generate an exhaustive dump profiling all applied system-level rules configurations (e.g., UFW states, /etc/hosts tables, traffic shaping rules, iptables custom chains).
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/get-rules \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

```
### GET /nodes/{node_id}/commands
 * **Description:** Lists chronological data execution tracking history entries maps for a node (latest first). Default retrieval limit size defaults to 20 elements.
```bash
curl -s "http://127.0.0.1:8000/nodes/1/commands?limit=20" | python3 -m json.tool

```
### GET /nodes/{node_id}/commands/{command_id}
 * **Description:** Extracts detailed metadata parameters tracking execution context parameters and output fields mapping to a target job index identifier.
```bash
curl -s http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-STRING-HERE | python3 -m json.tool

```
### DELETE /nodes/{node_id}/commands/{command_id}
 * **Description:** Drops a queued transaction from execution processing if the edge service entity has not evaluated it. Returns a 400 Bad Request code response standard error if processing operations have already executed.
```bash
curl -s -X DELETE http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-STRING-HERE

```
## 7. Command Queue — Agent Operations
> **Note:** Requires explicit **Bearer API Key Authentication**. Accessible only by target execution logic processes.
> 
### GET /nodes/{node_id}/commands/pending
 * **Description:** Pulls unexecuted operational instruction steps from the central server orchestration queue structure. **Crucial:** This routing path endpoint acts as the core system heartbeat monitor mechanism, updating the host lifecycle parameter field tracking metadata (last_seen) with every call. Polled by the agent every 10 seconds.
```bash
curl -s http://127.0.0.1:8000/nodes/1/commands/pending \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  | python3 -m json.tool

```
### POST /nodes/{node_id}/commands/{command_id}/result
 * **Description:** Transmits script execution details, tracking status context variables, and command-line execution payloads output data blobs back up from the edge host environment into the main console control registry database.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-STRING-HERE/result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU" \
  -d '{
    "success": true,
    "data": {"output": "Rule applied successfully"}
  }' | python3 -m json.tool

```

