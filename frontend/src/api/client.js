// Thin wrapper around fetch for the Argus backend.
// Base URL is configurable via .env (VITE_API_BASE_URL) so this can point
// at any deployment without code changes.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // response had no JSON body — keep statusText
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

// ---------- Nodes ----------
export const getNodes = () => request('/nodes');
export const getNode = (nodeId) => request(`/nodes/${nodeId}`);
export const getNodeStatus = (nodeId) => request(`/nodes/${nodeId}/status`);
export const getNodeDashboard = (nodeId) => request(`/nodes/${nodeId}/dashboard`);

// ---------- Telemetry (read-only) ----------
export const getStartupData = (nodeId) => request(`/nodes/${nodeId}/startup-data`);
export const getStartupDataHistory = (nodeId, limit = 10) =>
  request(`/nodes/${nodeId}/startup-data/history?limit=${limit}`);

export const getOneMinuteData = (nodeId) => request(`/nodes/${nodeId}/one-minute-data`);
export const getOneMinuteDataHistory = (nodeId, limit = 60) =>
  request(`/nodes/${nodeId}/one-minute-data/history?limit=${limit}`);

export const getFiveMinuteData = (nodeId) => request(`/nodes/${nodeId}/five-minute-data`);
export const getFiveMinuteDataHistory = (nodeId, limit = 288) =>
  request(`/nodes/${nodeId}/five-minute-data/history?limit=${limit}`);

export const getThirtyMinuteData = (nodeId) => request(`/nodes/${nodeId}/thirty-minute-data`);
export const getThirtyMinuteDataHistory = (nodeId, limit = 48) =>
  request(`/nodes/${nodeId}/thirty-minute-data/history?limit=${limit}`);

export const getDailyData = (nodeId) => request(`/nodes/${nodeId}/daily-data`);
export const getDailyDataHistory = (nodeId, limit = 30) =>
  request(`/nodes/${nodeId}/daily-data/history?limit=${limit}`);

// ---------- Firewall Rules (CRUD) ----------
export const getFirewallRules = (nodeId) => request(`/nodes/${nodeId}/firewall-rules`);
export const getFirewallRule = (nodeId, ruleId) =>
  request(`/nodes/${nodeId}/firewall-rules/${ruleId}`);
export const createFirewallRule = (nodeId, rule) =>
  request(`/nodes/${nodeId}/firewall-rules`, { method: 'POST', body: rule });
export const updateFirewallRule = (nodeId, ruleId, rule) =>
  request(`/nodes/${nodeId}/firewall-rules/${ruleId}`, { method: 'PUT', body: rule });
export const deleteFirewallRule = (nodeId, ruleId) =>
  request(`/nodes/${nodeId}/firewall-rules/${ruleId}`, { method: 'DELETE' });
export const getFirewallStatus = (nodeId) => request(`/nodes/${nodeId}/firewall-status`);

// ---------- Commands (create + manage) ----------
export const getCommands = (nodeId, limit = 20) =>
  request(`/nodes/${nodeId}/commands?limit=${limit}`);
export const getCommand = (nodeId, commandId) =>
  request(`/nodes/${nodeId}/commands/${commandId}`);
export const deleteCommand = (nodeId, commandId) =>
  request(`/nodes/${nodeId}/commands/${commandId}`, { method: 'DELETE' });

export const createRefreshCommand = (nodeId, collector) =>
  request(`/nodes/${nodeId}/commands/refresh`, { method: 'POST', body: { collector } });
export const createEnforceCommand = (nodeId, payload) =>
  request(`/nodes/${nodeId}/commands/enforce`, { method: 'POST', body: payload });
export const createDeleteRuleCommand = (nodeId, payload) =>
  request(`/nodes/${nodeId}/commands/delete-rule`, { method: 'POST', body: payload });
export const createGetRulesCommand = (nodeId) =>
  request(`/nodes/${nodeId}/commands/get-rules`, { method: 'POST' });

export { BASE_URL };
