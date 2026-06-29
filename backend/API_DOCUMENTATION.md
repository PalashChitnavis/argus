# Argus Backend - Complete API Implementation

## Overview
The backend has been updated to support all firewall rule types, command enforcement, and proper telemetry data retrieval as per the Argus Linux End-Node specification.

---

## Database Models

### 1. **FirewallRule** (Updated)
```
- rule_type: port | ip | ip_port | domain | bandwidth | user_port
- action: allow | deny | block | unblock | set | remove
- params: JSON (flexible structure based on rule_type)
- schedule: JSON (optional: {start_time: "HH:MM", end_time: "HH:MM"})
- enabled: Boolean
- applied: Boolean (whether applied to the node)
- description: String (optional)
```

### 2. **Command** (New)
```
- command_id: UUID (unique)
- node_id: Foreign key to Node
- command_type: refresh | enforce | delete_rule | get_rules
- payload: JSON (command-specific structure)
- executed: Boolean
- created_at, executed_at: Timestamps
```

### 3. **CommandResult** (New)
```
- command_id: Foreign key to Command
- success: Boolean
- error_message: String (optional)
- data: JSON (result data)
- created_at: Timestamp
```

---

## Rule Types & Parameters

### Port Rule
```json
{
  "rule_type": "port",
  "action": "allow" | "deny",
  "params": {
    "port": 22,
    "protocol": "tcp" | "udp" | "any",
    "direction": "in" | "out"
  }
}
```

### IP Rule
```json
{
  "rule_type": "ip",
  "action": "allow" | "deny",
  "params": {
    "ip": "192.168.1.50",
    "direction": "in" | "out"
  }
}
```

### IP+Port Rule
```json
{
  "rule_type": "ip_port",
  "action": "allow" | "deny",
  "params": {
    "ip": "10.0.0.5",
    "port": 5432,
    "protocol": "tcp" | "udp",
    "direction": "in" | "out"
  }
}
```

### Domain Rule
```json
{
  "rule_type": "domain",
  "action": "block" | "unblock",
  "params": {
    "domain": "facebook.com"
  }
}
```

### Bandwidth Rule
```json
{
  "rule_type": "bandwidth",
  "action": "set" | "remove",
  "params": {
    "rate_mbit": 1,
    "interface": "wlp8s0"
  }
}
```

### User+Port Rule
```json
{
  "rule_type": "user_port",
  "action": "block" | "unblock",
  "params": {
    "username": "palash",
    "port": 443,
    "protocol": "tcp" | "udp"
  }
}
```

### Time-Based Scheduling (Any Rule)
```json
{
  "rule_type": "domain",
  "action": "block",
  "params": { "domain": "youtube.com" },
  "schedule": {
    "start_time": "09:00",
    "end_time": "17:00"
  }
}
```

---

## API Endpoints

### Frontend Admin - Firewall Rules CRUD

**POST** `/nodes/{node_id}/firewall-rules`
- Create a new firewall rule
- Auto-generates enforce command if enabled
- Returns: FirewallRuleResponse

**GET** `/nodes/{node_id}/firewall-rules`
- List all rules for a node
- Returns: List[FirewallRuleResponse]

**GET** `/nodes/{node_id}/firewall-rules/{rule_id}`
- Get specific rule
- Returns: FirewallRuleResponse

**PUT** `/nodes/{node_id}/firewall-rules/{rule_id}`
- Update rule (marks as not applied)
- Auto-generates enforce or delete command as needed
- Returns: FirewallRuleResponse

**DELETE** `/nodes/{node_id}/firewall-rules/{rule_id}`
- Delete rule
- Auto-generates delete command if applied
- Returns: 204 No Content

---

### Frontend Admin - Command Creation

**POST** `/nodes/{node_id}/commands/refresh`
```json
{
  "collector": "network_interfaces|active_connections|firewall_status|etc"
}
```
- Create refresh command for specific collector

**POST** `/nodes/{node_id}/commands/enforce`
```json
{
  "rule_type": "port|ip|ip_port|domain|bandwidth|user_port",
  "action": "allow|deny|block|unblock|set|remove",
  "params": { ... },
  "schedule": { "start_time": "09:00", "end_time": "17:00" }  // optional
}
```
- Create enforce command for new rule

**POST** `/nodes/{node_id}/commands/delete-rule`
```json
{
  "rule_type": "firewall",
  "rule_number": 2
}
```
- Create delete command

**POST** `/nodes/{node_id}/commands/get-rules`
- Create get_rules command to fetch current enforcement state

---

### Frontend - Query Commands

**GET** `/nodes/{node_id}/commands`
- Get command history (limit: 20 default)
- Returns list with execution status and results

**GET** `/nodes/{node_id}/commands/{command_id}`
- Get specific command with result
- Returns command detail + result

**DELETE** `/nodes/{node_id}/commands/{command_id}`
- Delete unexecuted command
- Returns: 204 No Content

---

### Frontend - Firewall Status

**GET** `/nodes/{node_id}/firewall-status`
```json
{
  "node_id": 42,
  "total_rules": 5,
  "enabled_rules": 4,
  "applied_rules": 3,
  "pending_rules": 1,
  "rules_by_type": {
    "port": 2,
    "domain": 2,
    "bandwidth": 1
  }
}
```

---

### Linux End Node - Command Polling

**GET** `/nodes/{node_id}/commands/pending`
- Called every 10 seconds by node
- Returns pending commands
- Updates `last_seen` for online/offline tracking
```json
{
  "commands": [
    {
      "command_id": "uuid-here",
      "type": "refresh|enforce|delete_rule|get_rules",
      "payload": { ... }
    }
  ]
}
```

**POST** `/nodes/{node_id}/commands/{command_id}/result`
```json
{
  "node_id": 42,
  "command_id": "uuid-here",
  "success": true,
  "data": { ... },
  "error_message": null  // optional
}
```
- Report command execution result
- Marks command as executed

---

### Linux End Node - Firewall Status

**GET** `/nodes/{node_id}/firewall-rules/pending`
- Get enabled rules not yet applied
```json
{
  "node_id": 42,
  "pending_rules": [
    {
      "id": 1,
      "rule_type": "port",
      "action": "allow",
      "params": { "port": 22, "protocol": "tcp", "direction": "in" },
      "schedule": null,
      "description": "SSH access"
    }
  ]
}
```

**POST** `/nodes/{node_id}/firewall-rules/apply-status`
```json
{
  "rule_id": 1,
  "applied": true,
  "status": "success"  // or "failed"
}
```
- Report rule application status

---

## Frontend Endpoints - Telemetry Data Retrieval

### Node Management
- **GET** `/nodes` - List all nodes
- **GET** `/nodes/{node_id}` - Get node details
- **GET** `/nodes/{node_id}/status` - Online/offline status
- **GET** `/nodes/{node_id}/dashboard` - Combined dashboard

### Telemetry by Type
- **GET** `/nodes/{node_id}/startup-data` - Latest startup data
- **GET** `/nodes/{node_id}/startup-data/history?limit=10` - Historical
- **GET** `/nodes/{node_id}/one-minute-data` - Latest (CPU, processes)
- **GET** `/nodes/{node_id}/one-minute-data/history?limit=60` - Historical
- **GET** `/nodes/{node_id}/five-minute-data` - Latest (disk, RAM, network)
- **GET** `/nodes/{node_id}/five-minute-data/history?limit=288` - Historical (24h)
- **GET** `/nodes/{node_id}/thirty-minute-data` - Latest (security, network config)
- **GET** `/nodes/{node_id}/thirty-minute-data/history?limit=48` - Historical (24h)
- **GET** `/nodes/{node_id}/daily-data` - Latest daily snapshot
- **GET** `/nodes/{node_id}/daily-data/history?limit=30` - Historical (30 days)

---

## Workflow Example

### Admin Creates and Applies a Port Block

1. **Frontend creates rule:**
   ```
   POST /nodes/42/firewall-rules
   {
     "rule_type": "port",
     "action": "deny",
     "params": { "port": 80, "protocol": "tcp", "direction": "in" },
     "enabled": true,
     "description": "Block HTTP"
   }
   ```
   - ✅ Rule saved to database
   - ✅ Enforce command auto-created and stored

2. **Linux node polls for commands:**
   ```
   GET /nodes/42/commands/pending
   ```
   - Returns pending enforce command

3. **Linux node applies rule (UFW):**
   - `ufw deny in 80/tcp`
   - Saves rule state locally

4. **Linux node reports status:**
   ```
   POST /nodes/42/firewall-rules/apply-status
   { "rule_id": 1, "applied": true, "status": "success" }
   ```
   - ✅ Rule marked as applied in database

5. **Frontend queries status:**
   ```
   GET /nodes/42/firewall-status
   ```
   - Returns: 1 total rule, 1 enabled, 1 applied, 0 pending

---

## File Structure

```
argus-backend/
├── app/
│   ├── models/
│   │   ├── firewall_rule.py       ← Updated with JSON params/schedule
│   │   ├── command.py             ← New
│   │   └── __init__.py            ← Updated
│   ├── schemas/
│   │   ├── firewall.py            ← Updated
│   │   ├── firewall_commands.py   ← New (comprehensive schemas)
│   │   ├── telemetry.py           ← Existing (POST data)
│   │   ├── telemetry_read.py      ← New (GET data for frontend)
│   │   └── commands.py            ← Existing
│   ├── routers/
│   │   ├── firewall.py            ← Updated with commands
│   │   ├── commands.py            ← Updated with full implementation
│   │   ├── telemetry.py           ← Existing (POST endpoints)
│   │   ├── telemetry_read.py      ← New (GET endpoints)
│   │   └── register.py            ← Existing
│   ├── core/
│   │   └── auth.py                ← Existing (auth logic)
│   ├── db.py                      ← Existing
│   └── main.py                    ← Updated with new routers
└── init_db.py                     ← Creates all tables
```

---

## Key Features

✅ **Multiple Rule Types** - Supports port, IP, domain, bandwidth, per-user rules  
✅ **Time-Based Scheduling** - Schedule rules with start/end times  
✅ **Command System** - Enforce, delete, refresh, get_rules  
✅ **Flexible JSON Params** - Each rule type has specific params  
✅ **Command Tracking** - Full history with execution status  
✅ **Telemetry Retrieval** - GET endpoints for all data types  
✅ **Node Status** - Online/offline tracking via command polling  
✅ **Auto Command Generation** - Creating/updating/deleting rules auto-generates commands  

---

## Database Migration
Run once to create new tables:
```bash
source venv/bin/activate
python init_db.py
```

New tables created:
- `firewall_rules` (updated schema)
- `commands` (new)
- `command_results` (new)
