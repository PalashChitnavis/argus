#!/usr/bin/env bash
# Argus Backend — Automated Test Script
# Usage: bash test_argus.sh
# Requires: curl, python3
# Set NODE_ID and API_KEY below.

NODE_ID=1
API_KEY="xatXdDZtbdok0IiEdVB6pFfbCawtgbMLQda1lh_o-mU"
BASE="http://127.0.0.1:8000"
LOGFILE="argus_test.log"

G="\033[32m"; R="\033[31m"; Y="\033[33m"; B="\033[1;34m"; NC="\033[0m"
> "$LOGFILE"
PASS_COUNT=0; FAIL_COUNT=0

pass() { echo -e "${G}PASS${NC}  $1"; echo "PASS  $1" >> "$LOGFILE"; (( PASS_COUNT++ )); }
fail() { echo -e "${R}FAIL${NC}  $1"; echo "FAIL  $1" >> "$LOGFILE"; (( FAIL_COUNT++ )); }
info() { echo -e "${Y}INFO${NC}  $1"; echo "INFO  $1" >> "$LOGFILE"; }
sect() { echo -e "\n${B}=== $1 ===${NC}"; echo -e "\n=== $1 ===" >> "$LOGFILE"; }

# ── http helpers — write body to $BODY, status to $STATUS ──────────────────
# Strategy: write body to a tmp file, status goes to stdout via -w, body via -o

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

do_get() {
    local URL="$1" AUTH="${2:-}"
    if [[ -n "$AUTH" ]]; then
        STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" \
            -H "Authorization: Bearer $AUTH" "$BASE$URL")
    else
        STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" "$BASE$URL")
    fi
    BODY=$(cat "$TMPFILE")
}

do_post() {
    local URL="$1" DATA="$2" AUTH="${3:-}"
    if [[ -n "$AUTH" ]]; then
        STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $AUTH" \
            -d "$DATA" "$BASE$URL")
    else
        STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$DATA" "$BASE$URL")
    fi
    BODY=$(cat "$TMPFILE")
}

do_put() {
    local URL="$1" DATA="$2"
    STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" -X PUT \
        -H "Content-Type: application/json" \
        -d "$DATA" "$BASE$URL")
    BODY=$(cat "$TMPFILE")
}

do_delete() {
    local URL="$1"
    STATUS=$(curl -s -o "$TMPFILE" -w "%{http_code}" -X DELETE "$BASE$URL")
    BODY=$(cat "$TMPFILE")
}

assert() {
    local LABEL="$1" WANT="$2"
    echo "  HTTP $STATUS | $(echo "$BODY" | head -c 300)" >> "$LOGFILE"
    if [[ "$STATUS" == "$WANT" ]]; then
        pass "$LABEL"
    else
        fail "$LABEL  (expected $WANT, got $STATUS)"
        echo "  Body: $BODY" >> "$LOGFILE"
    fi
}

jget() { echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$2)" 2>/dev/null; }

wait_for_result() {
    local CMD_ID="$1" LABEL="$2" MAX=15 I=0
    info "Waiting up to ${MAX}s for agent to execute: $LABEL"
    while (( I < MAX )); do
        sleep 1; (( I++ ))
        do_get "/nodes/$NODE_ID/commands/$CMD_ID"
        local EXEC; EXEC=$(jget "$BODY" "['executed']")
        if [[ "$EXEC" == "True" ]]; then
            local SUCCESS; SUCCESS=$(jget "$BODY" "['result']['success']")
            if [[ "$SUCCESS" == "True" ]]; then
                pass "Agent executed: $LABEL"
                echo "$BODY" | python3 -m json.tool 2>/dev/null >> "$LOGFILE"
            else
                fail "Agent reported failure: $LABEL"
                echo "$BODY" >> "$LOGFILE"
            fi
            return
        fi
    done
    fail "Timed out waiting for agent: $LABEL"
}


# ════════════════════════════════════════════════════════════
sect "1 — NODE STATUS"
# ════════════════════════════════════════════════════════════

do_get "/nodes";           assert "GET /nodes" 200
do_get "/nodes/$NODE_ID";  assert "GET /nodes/$NODE_ID" 200
STATUS_VAL=$(jget "$BODY" "['status']")
info "Node status = $STATUS_VAL"
[[ "$STATUS_VAL" == "online" ]] && pass "Node is online" || fail "Node is $STATUS_VAL — is agent running?"

# ════════════════════════════════════════════════════════════
sect "2 — COMMAND POLL (auth checks)"
# ════════════════════════════════════════════════════════════

do_get "/nodes/$NODE_ID/commands/pending"
assert "GET pending commands (no auth → 403)" 403

do_get "/nodes/$NODE_ID/commands/pending" "$API_KEY"
assert "GET pending commands (valid key → 200)" 200

do_get "/nodes/$NODE_ID/commands/pending" "bad-key-000"
assert "GET pending commands (bad key → 401)" 401

# ════════════════════════════════════════════════════════════
sect "3 — TELEMETRY READ"
# ════════════════════════════════════════════════════════════

for TIER in startup-data one-minute-data five-minute-data thirty-minute-data daily-data; do
    do_get "/nodes/$NODE_ID/$TIER"
    assert "GET /nodes/$NODE_ID/$TIER" 200
    if [[ "$STATUS" == "200" ]]; then
        ID=$(jget "$BODY" "['id']"); TS=$(jget "$BODY" "['received_at']")
        info "  id=$ID  received_at=$TS"
    fi
done

do_get "/nodes/$NODE_ID/dashboard"; assert "GET /nodes/$NODE_ID/dashboard" 200

# ════════════════════════════════════════════════════════════
sect "4 — FIREWALL RULES CRUD"
# ════════════════════════════════════════════════════════════

# CREATE
do_post "/nodes/$NODE_ID/firewall-rules" '{
  "rule_type": "port",
  "action": "deny",
  "params": {"port": 19999, "protocol": "tcp", "direction": "in"},
  "enabled": true,
  "description": "argus-test: block 19999"
}'
assert "POST firewall-rules (port deny 19999)" 201
RULE_ID=$(jget "$BODY" "['id']")
info "Created rule id=$RULE_ID"

# READ list
do_get "/nodes/$NODE_ID/firewall-rules"; assert "GET firewall-rules (list)" 200

# READ single
do_get "/nodes/$NODE_ID/firewall-rules/$RULE_ID"; assert "GET firewall-rules/$RULE_ID" 200
info "  rule_type=$(jget "$BODY" "['rule_type']")  enabled=$(jget "$BODY" "['enabled']")"

# UPDATE disable
do_put "/nodes/$NODE_ID/firewall-rules/$RULE_ID" '{"enabled": false}'
assert "PUT firewall-rules/$RULE_ID (disable)" 200
info "  enabled=$(jget "$BODY" "['enabled']")"

# UPDATE re-enable
do_put "/nodes/$NODE_ID/firewall-rules/$RULE_ID" '{"enabled": true}'
assert "PUT firewall-rules/$RULE_ID (re-enable)" 200
info "  enabled=$(jget "$BODY" "['enabled']")"

# UPDATE description only
do_put "/nodes/$NODE_ID/firewall-rules/$RULE_ID" '{"description": "argus-test: updated"}'
assert "PUT firewall-rules/$RULE_ID (description)" 200

# READ 404
do_get "/nodes/$NODE_ID/firewall-rules/99999"; assert "GET firewall-rules/99999 (→ 404)" 404

# DELETE
do_delete "/nodes/$NODE_ID/firewall-rules/$RULE_ID"; assert "DELETE firewall-rules/$RULE_ID" 204

# Confirm deleted
do_get "/nodes/$NODE_ID/firewall-rules/$RULE_ID"; assert "GET deleted rule (→ 404)" 404

# Firewall status summary
do_get "/nodes/$NODE_ID/firewall-status"; assert "GET firewall-status" 200
info "  total=$(jget "$BODY" "['total_rules']")  enabled=$(jget "$BODY" "['enabled_rules']")"

# ════════════════════════════════════════════════════════════
sect "5 — ENFORCE COMMANDS + AGENT EXECUTION"
# ════════════════════════════════════════════════════════════

# 5a port deny
do_post "/nodes/$NODE_ID/commands/enforce" '{
  "rule_type": "port",
  "action": "deny",
  "params": {"port": 29999, "protocol": "tcp", "direction": "in"}
}'
assert "POST commands/enforce (port deny 29999)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "port deny 29999"
info "Verify: sudo ufw status numbered | grep 29999"

# 5b ip deny
do_post "/nodes/$NODE_ID/commands/enforce" '{
  "rule_type": "ip",
  "action": "deny",
  "params": {"ip": "192.0.2.1", "direction": "in"}
}'
assert "POST commands/enforce (ip deny 192.0.2.1)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "ip deny 192.0.2.1"
info "Verify: sudo ufw status numbered | grep 192.0.2.1"

# 5c domain block
do_post "/nodes/$NODE_ID/commands/enforce" '{
  "rule_type": "domain",
  "action": "block",
  "params": {"domain": "argus-test-block.invalid"}
}'
assert "POST commands/enforce (domain block)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "domain block argus-test-block.invalid"
info "Verify: grep argus-test-block.invalid /etc/hosts"

# ════════════════════════════════════════════════════════════
sect "6 — DELETE RULE COMMANDS + AGENT EXECUTION"
# ════════════════════════════════════════════════════════════

# 6a domain unblock
do_post "/nodes/$NODE_ID/commands/delete-rule" '{
  "rule_type": "domain",
  "domain": "argus-test-block.invalid"
}'
assert "POST commands/delete-rule (domain unblock)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "domain unblock argus-test-block.invalid"
info "Verify: grep argus-test-block.invalid /etc/hosts  ← should be empty"

# 6b ufw delete by rule number
info "Checking current ufw rules before deleting rule #1..."
do_post "/nodes/$NODE_ID/commands/delete-rule" '{
  "rule_type": "firewall",
  "rule_number": 1
}'
assert "POST commands/delete-rule (ufw rule #1)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "ufw delete rule #1"
info "Verify: sudo ufw status numbered"

# ════════════════════════════════════════════════════════════
sect "7 — REFRESH + GET_RULES COMMANDS"
# ════════════════════════════════════════════════════════════

do_post "/nodes/$NODE_ID/commands/refresh" '{"collector": "firewall_status"}'
assert "POST commands/refresh (firewall_status)" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "refresh firewall_status"
do_get "/nodes/$NODE_ID/commands/$CMD_ID"
info "Live firewall_status from agent:"
echo "$BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=(d.get('result') or {})
print(json.dumps(r.get('data',{}), indent=2))
" 2>/dev/null | tee -a "$LOGFILE"

do_post "/nodes/$NODE_ID/commands/get-rules" '{}'
assert "POST commands/get-rules" 201
CMD_ID=$(jget "$BODY" "['command_id']")
wait_for_result "$CMD_ID" "get_rules"
do_get "/nodes/$NODE_ID/commands/$CMD_ID"
info "Agent enforcement snapshot:"
echo "$BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=(d.get('result') or {})
print(json.dumps(r.get('data',{}), indent=2))
" 2>/dev/null | tee -a "$LOGFILE"

# ════════════════════════════════════════════════════════════
sect "8 — COMMAND HISTORY"
# ════════════════════════════════════════════════════════════

do_get "/nodes/$NODE_ID/commands?limit=20"; assert "GET commands history" 200
COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
info "Commands in history: $COUNT"

# ════════════════════════════════════════════════════════════
sect "9 — TELEMETRY HISTORY"
# ════════════════════════════════════════════════════════════

for TIER in startup-data one-minute-data five-minute-data thirty-minute-data; do
    do_get "/nodes/$NODE_ID/$TIER/history?limit=3"
    assert "GET $TIER/history" 200
    COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
    info "  $TIER: $COUNT records"
done

# ════════════════════════════════════════════════════════════
sect "10 — ONLINE/OFFLINE STATUS"
# ════════════════════════════════════════════════════════════

do_get "/nodes/$NODE_ID/status"; assert "GET /nodes/$NODE_ID/status" 200
info "status=$(jget "$BODY" "['status']")  last_seen=$(jget "$BODY" "['last_seen']")"

# ════════════════════════════════════════════════════════════
sect "SUMMARY"
# ════════════════════════════════════════════════════════════

TOTAL=$(( PASS_COUNT + FAIL_COUNT ))
echo ""
echo -e "  ${G}PASSED${NC}: $PASS_COUNT / $TOTAL"
echo -e "  ${R}FAILED${NC}: $FAIL_COUNT / $TOTAL"
echo ""
echo "Full log → $LOGFILE"

if (( FAIL_COUNT > 0 )); then
    echo -e "\n${R}Failed tests:${NC}"
    grep "^FAIL" "$LOGFILE"
fi