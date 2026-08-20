# Argus Backend — API Documentation

## Overview
The backend is a FastAPI service with four responsibilities: node registration,
telemetry ingest (from the Linux agent), telemetry read (for the admin
frontend), and firewall rule management + command dispatch. Every endpoint
below is live in `app/main.py` — nothing here is aspirational.

Auth comes in two flavors:
- **Bearer API key** (`get_current_node`) — used by the Linux agent for
  ingest, command polling, and result reporting. The key is hashed
  (`api_key_hash`) before being stored; the raw key is only ever shown once,
  at registration.
- **None** — used by the admin frontend for every read endpoint and for
  firewall/command management. There's no admin auth layer yet (see
  "Known gaps" at the end).

---

## 1. Registration

**POST** `/register`
- First-time node registration. Consumes a single-use enrollment token.
- Auth: none (the enrollment token itself is the credential, checked in the body).
- Body: `{ enrollment_token, machine_id, hostname }`
- Returns: `{ node_id, api_key }` — the agent saves `api_key` locally
  (`credentials.json`) and uses it as the Bearer token for every ingest call
  from then on. It is not retrievable again.

---

## 2. Telemetry Ingest — `/telemetry/*`

All ingest endpoints live in `app/routers/telemetry.py`, share the
`/telemetry` prefix, require the Bearer API key, and are called exclusively
by the agent on its own schedule (the backend doesn't enforce cadence — it
just accepts whatever arrives). Each returns `{"status": "ok"}` with
`201 Created` on success.

| Endpoint | Cadence | Payload |
|---|---|---|
| `POST /telemetry/startup` | once, on agent boot | `machine_id`, optional `os_info`, `hardware_info`, `installed_packages[]` |
| `POST /telemetry/os-info` | daily | `machine_id`, `os_info` |
| `POST /telemetry/hardware-info` | daily | `machine_id`, `hardware_info` |
| `POST /telemetry/installed-packages` | daily | `machine_id`, `installed_packages[]` |
| `POST /telemetry/cpu` | 1 min | `machine_id`, `cpu_percent_used` |
| `POST /telemetry/processes` | 1 min | `machine_id`, `new_processes[]` (diff since last poll, not a full snapshot) |
| `POST /telemetry/disk` | 5 min | `machine_id`, `disk_used_gb`, `disk_free_gb`, `disk_percent_used` |
| `POST /telemetry/ram` | 5 min | `machine_id`, `ram_used_gb`, `ram_available_gb`, `ram_percent_used` |
| `POST /telemetry/network-io` | 5 min | `machine_id`, `bytes_sent_mb`, `bytes_recv_mb` |
| `POST /telemetry/active-connections` | 5 min | `machine_id`, `connections[]` |
| `POST /telemetry/system-logs` | 5 min | `machine_id`, `log_lines[]` |
| `POST /telemetry/auth-events` | 5 min | `machine_id`, `log_lines[]` |
| `POST /telemetry/browser-history` | 10 min | `machine_id`, `most_visited[]`, `recently_visited[]` |
| `POST /telemetry/network-interfaces` | 30 min | `machine_id`, `interfaces[]` |
| `POST /telemetry/dns-servers` | 30 min | `machine_id`, `dns_servers[]` |
| `POST /telemetry/routing-table` | 30 min | `machine_id`, `routing_table[]` |
| `POST /telemetry/security-status` | 30 min | `machine_id`, firewall/SSH/MAC posture fields |

Full field-level shapes are in `app/schemas/telemetry.py` — every field
maps 1:1 to a column in the matching model under `app/models/`.

Every "batched" telemetry type (`active-connections`, `system-logs`,
`auth-events`, `browser-history`, `network-interfaces` +
`dns-servers` + `routing-table`) is stored with a shared `batch_id` (UUID)
so all rows from one collection cycle can be retrieved together.

---

## 3. Telemetry Read — `/nodes/{node_id}/...`

All read endpoints live in `app/routers/nodes_read.py`, require no auth
(admin frontend only), and return `404` if `node_id` doesn't exist.

### Node identity
| Endpoint | Description |
|---|---|
| `GET /nodes` | List all nodes with derived online/offline status. |
| `GET /nodes/{node_id}` | Single node detail. |
| `GET /nodes/{node_id}/status` | `{ node_id, status, last_seen }` — online if `last_seen` is within 30s. |
| `GET /nodes/{node_id}/overview` | Combined dashboard payload — node identity, OS/hardware, latest CPU/RAM/disk/network-io, latest security status, top 5 visited domains (from the latest browser-history batch), active connection count, and process count in the last hour. This is what the frontend's overview page loads in one call. |

### Per-collector data
Each of these has a `/history` variant with a `limit` query param (defaults
vary by type — see table) except where noted otherwise.

| Endpoint | Notes |
|---|---|
| `GET /nodes/{node_id}/os-info` | Latest only, no history (identity rarely changes). |
| `GET /nodes/{node_id}/hardware-info` | Latest only. |
| `GET /nodes/{node_id}/cpu` + `/cpu/history?limit=60` | |
| `GET /nodes/{node_id}/ram` + `/ram/history?limit=60` | |
| `GET /nodes/{node_id}/disk` + `/disk/history?limit=60` | |
| `GET /nodes/{node_id}/network-io` + `/network-io/history?limit=60` | |
| `GET /nodes/{node_id}/processes/history?limit=15&offset=0` | **Paginated.** Returns `{ items[], total, limit, offset }`. No "latest" variant — each cycle can report zero-to-many new processes, so there's no single "current" row. |
| `GET /nodes/{node_id}/active-connections?limit=15&offset=0` | **Paginated.** Returns the most recent batch: `{ batch_id, received_at, connections[], total, limit, offset }`. `total` is the full connection count in that batch, independent of the page you're on. |
| `GET /nodes/{node_id}/system-logs` | Latest batch: `{ batch_id, received_at, log_lines[] }`. |
| `GET /nodes/{node_id}/auth-events` | Same shape as system-logs. |
| `GET /nodes/{node_id}/browser-history` | Latest batch: `{ batch_id, received_at, most_visited[], recently_visited[] }`. |
| `GET /nodes/{node_id}/network-config` | Latest batch: `{ batch_id, received_at, interfaces[], dns_servers[], routing_table[] }`. |
| `GET /nodes/{node_id}/security-status` + `/security-status/history?limit=48` | |
| `GET /nodes/{node_id}/installed-packages` | Latest batch: `{ batch_id, received_at, packages[] }`. |

**Pagination shape:** any endpoint above marked "paginated" takes `limit`
and `offset` query params and returns `total` alongside its results, so the
frontend can compute page count as `Math.ceil(total / limit)` without a
separate count call.

---

## 4. Firewall Rules — `/nodes/{node_id}/firewall-rules`

No auth (admin frontend). Full CRUD plus two agent-facing endpoints.

### Rule types & params
| `rule_type` | `action` | `params` |
|---|---|---|
| `port` | `allow` \| `deny` | `{ port, protocol: tcp\|udp\|any, direction: in\|out }` |
| `ip` | `allow` \| `deny` | `{ ip, direction: in\|out }` |
| `ip_port` | `allow` \| `deny` | `{ ip, port, protocol: tcp\|udp, direction: in\|out }` |
| `domain` | `block` \| `unblock` | `{ domain }` |
| `bandwidth` | `set` \| `remove` | `{ rate_mbit, interface }` |
| `user_port` | `block` \| `unblock` | `{ username, port, protocol: tcp\|udp }` |

Any rule can carry an optional `schedule: { start_time: "HH:MM", end_time: "HH:MM" }`.
The agent evaluates the window on every poll cycle (`now` between
`start_time` and `end_time`), not at an exact clock time — see the project
report for why exact-time scheduling was dropped.

### Admin (frontend) endpoints
| Endpoint | Description |
|---|---|
| `POST /nodes/{node_id}/firewall-rules` | Create a rule. Auto-generates an `enforce` command if `enabled: true`. |
| `GET /nodes/{node_id}/firewall-rules` | List all rules for a node. |
| `GET /nodes/{node_id}/firewall-rules/{rule_id}` | Single rule detail. |
| `PUT /nodes/{node_id}/firewall-rules/{rule_id}` | Partial update. Marks `applied: false`; auto-generates a fresh `enforce` or `delete_rule` command depending on the transition. |
| `DELETE /nodes/{node_id}/firewall-rules/{rule_id}` | `204`. Auto-generates a `delete_rule` command if the rule was applied. |
| `GET /nodes/{node_id}/firewall-status` | Rule counts: `{ node_id, total_rules, enabled_rules, applied_rules, pending_rules, rules_by_type }`. |

### Agent endpoints (Bearer auth)
| Endpoint | Description |
|---|---|
| `GET /nodes/{node_id}/firewall-rules/pending` | Enabled rules not yet applied (`applied: false`). |
| `POST /nodes/{node_id}/firewall-rules/apply-status` | Agent reports the outcome: `{ rule_id, applied, status: "success"\|"failed" }`. |

---

## 5. Commands — `/nodes/{node_id}/commands`

The command queue is how the admin frontend pushes work to a node between
its normal telemetry pushes: refresh a specific collector on demand, enforce
or delete a firewall rule immediately, or dump the full current rule state.

### Admin (frontend) — create commands, no auth
| Endpoint | Body |
|---|---|
| `POST /nodes/{node_id}/commands/refresh` | `{ collector }` — one of `network_interfaces`, `active_connections`, `dns_servers`, `routing_table`, `disk_usage`, `ram_usage`, `cpu_usage`, `network_io`, `running_processes`, `firewall_status`, `firewall_rules`, `all_rules`. |
| `POST /nodes/{node_id}/commands/enforce` | `{ rule_type, action, params, schedule? }` — same shape as a firewall rule. |
| `POST /nodes/{node_id}/commands/delete-rule` | `{ rule_type: "firewall", rule_number }` or `{ rule_type: "domain", domain }`. |
| `POST /nodes/{node_id}/commands/get-rules` | No body. Asks the agent to dump everything it currently has enforced (UFW/iptables state, `/etc/hosts` entries, tc rules). |

### Admin (frontend) — query commands, no auth
| Endpoint | Description |
|---|---|
| `GET /nodes/{node_id}/commands?limit=20` | Command history, most recent first. **Not paginated** — `limit` only, no `offset`. See "Known gaps" below. |
| `GET /nodes/{node_id}/commands/{command_id}` | Single command + its result, if any. |
| `DELETE /nodes/{node_id}/commands/{command_id}` | `204`. Only works if the command hasn't been executed yet (`400` otherwise). |

### Agent — poll and report, Bearer auth
| Endpoint | Description |
|---|---|
| `GET /nodes/{node_id}/commands/pending` | Polled every 10s. Returns unexecuted commands. **This call also updates `last_seen`** — it's the online/offline heartbeat, not just command delivery. |
| `POST /nodes/{node_id}/commands/{command_id}/result` | `{ success, data?, error_message? }`. Marks the command executed. |

---

## 6. Anomaly Detection — `/nodes/{node_id}/anomaly-scan`, `/anomalies`

Lives in `app/routers/anomaly.py` + `app/services/anomaly_detection.py`. No
auth (admin frontend only), `404` if `node_id` doesn't exist.

**Approach:** telemetry from every collector (CPU, RAM, disk, network I/O,
new processes, active connections, browser visits, system logs, auth
events) is bucketed into 5-minute windows per node, and one feature vector
is built per window (15 features — see `FEATURE_NAMES` in
`anomaly_detection.py`; missing signals in a window default to `0.0`).
`IsolationForest` (`contamination=0.1`, fixed not `"auto"`) is fit fresh on
the node's own recent windows on every scan call — there's no persisted
model file, and no cross-node state. This mirrors the project's other ML
scoping decisions (see project report): the "normal" baseline is always
that node's own recent behaviour, not a global model.

| Endpoint | Description |
|---|---|
| `POST /nodes/{node_id}/anomaly-scan?hours=6` | Refits the model on the last `hours` of telemetry and upserts flagged windows into `anomaly_results`, keyed on `(node_id, window_start)` — re-scanning the same window updates it rather than duplicating it. Returns `{ node_id, scan_range_start, scan_range_end, windows_scanned, anomalies_found, anomalies[], message }`. `message` is set (and `anomalies` empty) if fewer than `MIN_WINDOWS_REQUIRED` (6) windows are available yet. |
| `GET /nodes/{node_id}/anomalies?include_dismissed=false&limit=50` | List stored results, most recent window first. Dismissed rows excluded by default. |
| `PATCH /nodes/{node_id}/anomalies/{anomaly_id}/dismiss` | Marks one reviewed (`dismissed: true`, `dismissed_at` set). |

Each stored/returned anomaly includes:
- `anomaly_score` — IsolationForest's `decision_function` value; more negative = more anomalous.
- `features` — the raw 15-feature vector for that window.
- `contributing_features` — the top 3 features by `|z-score|` against the mean/stdev of that same feature across all windows in the scan, so the frontend can show *why* a window was flagged (e.g. `auth_event_count` spiking 4.8 standard deviations above normal).

For testing or demoing without waiting ~30 min for real agent data to
accumulate 6+ windows, run `python backend/seed_anomaly_demo_data.py <node_id>`
— it backfills 2 hours of synthetic telemetry with one injected spike
(CPU pegged, a burst of new processes, and an auth-failure cluster from
many distinct IPs) so a scan immediately has something to flag.

---

## Known gaps

- **`GET /nodes/{node_id}/commands`** takes `limit` but not `offset` — it's
  not paginated the way processes/active-connections now are. Low priority
  since command history is usually short-lived and demo-scale, but worth
  matching if the pattern gets reused elsewhere.
- **No admin auth.** Every frontend-facing endpoint (firewall CRUD, command
  creation, all telemetry reads) is open with no credential check. Fine for
  a local demo, explicitly out of scope for this build (see project report,
  "Scope discipline").
- **Enrollment tokens are stored as plaintext high-entropy strings** — a
  deliberate decision (single-use, short-lived, not the ongoing credential),
  not an oversight. Once used to register, the agent's actual ongoing
  credential is the API key, which **is** hashed server-side (SHA-256, via
  `hash_api_key()` in `app/core/security.py`) — only the hash is stored, and
  the raw key is shown to the agent exactly once, at registration.
- **Anomaly detection's `contamination=0.1` is fixed, not adaptive.** On a
  scan with few windows (e.g. 24), IsolationForest will flag roughly 10% of
  them regardless of how genuinely anomalous they are — expect 2-3 flagged
  windows on a quiet demo dataset even without an injected spike. This is a
  known tradeoff of a fixed contamination rate on small sample sizes, not a
  bug; a larger telemetry history evens this out.