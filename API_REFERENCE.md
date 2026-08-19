# Argus API Reference

Runnable curl examples for every live endpoint. For request/response schema
detail beyond what's inlined here, see `backend/API_DOCUMENTATION.md`.

## Global Environment Configuration
> **Base URL:** http://127.0.0.1:8000
>
> **Node ID:** 1 (used throughout as an example — substitute your own)
>
> **API Key:** `<agent's api_key, from the /register response>`
>
> **Enrollment Token:** `<generate one with backend/generate_token.py>`

> ⚠️ Don't commit real tokens/keys into this file — the values above are
> placeholders on purpose. Generate your own locally with
> `python generate_token.py` (see `backend/token_management.bash` for the
> full token-lifecycle commands: list, revoke, regenerate).

---

## 1. Registration

### POST /register
* **Description:** First-time node registration. Consumes the enrollment token (single use). Returns `node_id` and `api_key`, which the agent saves locally to `credentials.json`. The `api_key` is shown exactly once here — the backend only ever stores its SHA-256 hash after this.
* **Caller:** linux agent (on first boot)
* **Authentication:** None (the enrollment token in the body is the credential)
```bash
curl -s -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "enrollment_token": "<your enrollment token>",
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "hostname": "palash"
  }' | python3 -m json.tool

```

---

## 2. Telemetry Ingest — `/telemetry/*`
> **Note:** All ingest endpoints require **Bearer API Key Authentication** and are called exclusively by the linux agent on its own collection schedule.

### POST /telemetry/startup
* **Description:** Stores OS info, hardware specs, and the initial installed-packages list. Sent once on agent boot.
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/startup \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "hostname": "palash",
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

### POST /telemetry/cpu
* **Description:** CPU usage. Sent every 1 minute.
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/cpu \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "cpu_percent_used": 14.3
  }' | python3 -m json.tool

```

### POST /telemetry/processes
* **Description:** New processes seen since the last poll (a diff, not a full snapshot). Sent every 1 minute.
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/processes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
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

### POST /telemetry/disk, /telemetry/ram, /telemetry/network-io, /telemetry/active-connections, /telemetry/system-logs, /telemetry/auth-events
* **Description:** Disk, RAM, network I/O, active connections, recent syslog lines, and auth events. Sent every 5 minutes (one POST per type — these were a single combined payload in an earlier schema version, now split by collector).
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/disk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "disk_used_gb": 42.52,
    "disk_free_gb": 178.23,
    "disk_percent_used": 19.3
  }' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8000/telemetry/active-connections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
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
    ]
  }' | python3 -m json.tool

```

### POST /telemetry/browser-history
* **Description:** Most-visited and recently-visited sites across Chrome/Brave/Edge/Firefox. Sent every 10 minutes.
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/browser-history \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "most_visited": [
      {"domain": "github.com", "visit_count": 42, "browsers": ["chrome"], "title": "GitHub"}
    ],
    "recently_visited": [
      {"url": "https://github.com/PalashChitnavis/argus", "domain": "github.com", "browser": "chrome"}
    ]
  }' | python3 -m json.tool

```

### POST /telemetry/network-interfaces, /telemetry/dns-servers, /telemetry/routing-table, /telemetry/security-status
* **Description:** Network config and security posture (firewall, disk encryption, SSH config, AppArmor/SELinux). Sent every 30 minutes.
```bash
curl -s -X POST http://127.0.0.1:8000/telemetry/security-status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "machine_id": "fb61853188134b5fb0031eb6bdd6d63e",
    "firewall_tool": "ufw",
    "firewall_active": true,
    "disk_encrypted": false,
    "root_login_permitted": false,
    "password_auth_permitted": false,
    "mac_tool": "apparmor",
    "mac_enabled": true
  }' | python3 -m json.tool

```

### POST /telemetry/os-info, /telemetry/hardware-info, /telemetry/installed-packages
* **Description:** Daily baseline sync — same fields as the `startup` payload, split by type, sent once daily at 03:00.

---

## 3. Telemetry Read
> **Note:** These read endpoints require **No Authentication** and are called by the frontend.

| Endpoint | Description |
|---|---|
| GET /nodes | Lists all registered nodes with derived online/offline status. |
| GET /nodes/{node_id} | Node identity + status. |
| GET /nodes/{node_id}/status | `{ node_id, status, last_seen }`. Online if `last_seen` is within the trailing 30 seconds. |
| GET /nodes/{node_id}/overview | Combined dashboard payload: identity, OS/hardware, latest CPU/RAM/disk/network-io, latest security status, top 5 visited domains, active connection count, process count in the last hour. |
| GET /nodes/{node_id}/os-info | Latest OS info (no history — rarely changes). |
| GET /nodes/{node_id}/hardware-info | Latest hardware info (no history). |
| GET /nodes/{node_id}/cpu | Latest CPU snapshot. |
| GET /nodes/{node_id}/cpu/history?limit=60 | Historical CPU snapshots, most recent first. |
| GET /nodes/{node_id}/ram, /ram/history?limit=60 | Same pattern for RAM. |
| GET /nodes/{node_id}/disk, /disk/history?limit=60 | Same pattern for disk. |
| GET /nodes/{node_id}/network-io, /network-io/history?limit=60 | Same pattern for network I/O. |
| GET /nodes/{node_id}/processes/history?limit=15&offset=0 | **Paginated.** `{ items[], total, limit, offset }`. No single "latest" — each cycle can report zero-to-many new processes. |
| GET /nodes/{node_id}/active-connections?limit=15&offset=0 | **Paginated.** Most recent batch: `{ batch_id, received_at, connections[], total, limit, offset }`. |
| GET /nodes/{node_id}/system-logs | Latest batch: `{ batch_id, received_at, log_lines[] }`. |
| GET /nodes/{node_id}/auth-events | Same shape as system-logs. |
| GET /nodes/{node_id}/browser-history | Latest batch: `{ batch_id, received_at, most_visited[], recently_visited[] }`. |
| GET /nodes/{node_id}/network-config | Latest batch: `{ batch_id, received_at, interfaces[], dns_servers[], routing_table[] }`. |
| GET /nodes/{node_id}/security-status, /security-status/history?limit=48 | Latest + historical security posture. |
| GET /nodes/{node_id}/installed-packages | Latest batch: `{ batch_id, received_at, packages[] }`. |

### Example Telemetry Read Operations
```bash
# Online status
curl -s http://127.0.0.1:8000/nodes/1/status | python3 -m json.tool

# Combined dashboard payload
curl -s http://127.0.0.1:8000/nodes/1/overview | python3 -m json.tool

# Historical metrics with custom limits
curl -s "http://127.0.0.1:8000/nodes/1/cpu/history?limit=10" | python3 -m json.tool
curl -s "http://127.0.0.1:8000/nodes/1/security-status/history?limit=5" | python3 -m json.tool

# Paginated processes / connections — page 2, 15 per page
curl -s "http://127.0.0.1:8000/nodes/1/processes/history?limit=15&offset=15" | python3 -m json.tool
curl -s "http://127.0.0.1:8000/nodes/1/active-connections?limit=15&offset=15" | python3 -m json.tool

```

---

## 4. Firewall Rules CRUD (Admin Management)
> **Note:** No authentication — called directly by the frontend. Creating or enabling a rule auto-queues an `enforce` command for the agent to pick up. Disabling or deleting a rule auto-queues a `delete_rule` command.

### POST /nodes/{node_id}/firewall-rules
* **Description:** Create a rule. Supported `rule_type` values: `port`, `ip`, `ip_port`, `domain`, `bandwidth`, `user_port`.

#### Variant: Port rule
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

#### Variant: IP rule
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

#### Variant: IP + port rule
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

#### Variant: Domain block (/etc/hosts)
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

#### Variant: Bandwidth shaping (tc)
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

#### Variant: Per-user, per-port block (iptables)
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

#### Variant: Time-windowed schedule (any rule type)
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
* **Description:** List all rules for a node.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules | python3 -m json.tool

```

### GET /nodes/{node_id}/firewall-rules/{rule_id}
* **Description:** Single rule detail.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules/1 | python3 -m json.tool

```

### PUT /nodes/{node_id}/firewall-rules/{rule_id}
* **Description:** Partial update. Marks the rule `applied: false`; toggling `enabled: false` queues a `delete_rule` command, toggling it back to `true` queues a fresh `enforce` command.
```bash
# Disable a rule
curl -s -X PUT http://127.0.0.1:8000/nodes/1/firewall-rules/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}' | python3 -m json.tool

# Re-enable it
curl -s -X PUT http://127.0.0.1:8000/nodes/1/firewall-rules/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}' | python3 -m json.tool

```

### DELETE /nodes/{node_id}/firewall-rules/{rule_id}
* **Description:** `204 No Content`. If the rule was applied (`applied: true`), also queues a `delete_rule` command.
```bash
curl -s -X DELETE http://127.0.0.1:8000/nodes/1/firewall-rules/1

```

### GET /nodes/{node_id}/firewall-status
* **Description:** Rule counts by state and type.
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-status | python3 -m json.tool

```

---

## 5. Firewall Rules — Agent Endpoints
> **Note:** Requires **Bearer API Key Authentication**. Called by the linux agent only.

### GET /nodes/{node_id}/firewall-rules/pending
* **Description:** Enabled rules not yet applied (`applied: false`).
```bash
curl -s http://127.0.0.1:8000/nodes/1/firewall-rules/pending \
  -H "Authorization: Bearer <api_key>" \
  | python3 -m json.tool

```

### POST /nodes/{node_id}/firewall-rules/apply-status
* **Description:** Agent reports whether a rule was applied successfully.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/firewall-rules/apply-status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "rule_id": 1,
    "applied": true,
    "status": "success"
  }' | python3 -m json.tool

```

---

## 6. Command Queue — Admin Control
> **Note:** No authentication — called by the frontend.

### POST /nodes/{node_id}/commands/enforce
* **Description:** Queue an enforce command for a rule that isn't necessarily persisted as a `FirewallRule` row — useful for one-off ad-hoc enforcement. Picked up by the agent within ~10s (its poll interval).
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/enforce \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "port",
    "action": "deny",
    "params": {"port": 9090, "protocol": "tcp", "direction": "in"}
  }' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/enforce \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "ip",
    "action": "deny",
    "params": {"ip": "1.2.3.4", "direction": "in"}
  }' | python3 -m json.tool

```

### POST /nodes/{node_id}/commands/delete-rule
* **Description:** Tear down a specific rule on the node directly (by index or by domain), independent of any `FirewallRule` row.
```bash
# UFW rule by numbered index
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/delete-rule \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "firewall",
    "rule_number": 1
  }' | python3 -m json.tool

# Domain block
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/delete-rule \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "domain",
    "domain": "youtube.com"
  }' | python3 -m json.tool

```

### POST /nodes/{node_id}/commands/refresh
* **Description:** Force the agent to re-run one collector immediately, out of its normal schedule. Result lands back within ~10s.
* **Collector options:** `network_interfaces`, `active_connections`, `dns_servers`, `routing_table`, `disk_usage`, `ram_usage`, `cpu_usage`, `network_io`, `running_processes`, `firewall_status`, `firewall_rules`, `all_rules`.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/refresh \
  -H "Content-Type: application/json" \
  -d '{"collector": "active_connections"}' | python3 -m json.tool

```

### POST /nodes/{node_id}/commands/get-rules
* **Description:** Ask the agent to dump everything it currently has enforced (UFW/iptables state, `/etc/hosts` entries, tc rules).
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/get-rules \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

```

### GET /nodes/{node_id}/commands
* **Description:** Command history, most recent first. Defaults to 20. **Not paginated** — `limit` only, no `offset`.
```bash
curl -s "http://127.0.0.1:8000/nodes/1/commands?limit=20" | python3 -m json.tool

```

### GET /nodes/{node_id}/commands/{command_id}
* **Description:** Single command with its result, if any.
```bash
curl -s http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-HERE | python3 -m json.tool

```

### DELETE /nodes/{node_id}/commands/{command_id}
* **Description:** `204`. Only works if the command hasn't been executed yet — `400` otherwise.
```bash
curl -s -X DELETE http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-HERE

```

---

## 7. Command Queue — Agent Operations
> **Note:** Requires **Bearer API Key Authentication**. Called by the linux agent only.

### GET /nodes/{node_id}/commands/pending
* **Description:** Unexecuted commands for this node. Polled every 10 seconds. **This call also updates `last_seen`** — it's the online/offline heartbeat mechanism, not just command delivery.
```bash
curl -s http://127.0.0.1:8000/nodes/1/commands/pending \
  -H "Authorization: Bearer <api_key>" \
  | python3 -m json.tool

```

### POST /nodes/{node_id}/commands/{command_id}/result
* **Description:** Report execution outcome back to the server. Marks the command executed.
```bash
curl -s -X POST http://127.0.0.1:8000/nodes/1/commands/COMMAND-UUID-HERE/result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{
    "success": true,
    "data": {"output": "Rule applied successfully"}
  }' | python3 -m json.tool

```