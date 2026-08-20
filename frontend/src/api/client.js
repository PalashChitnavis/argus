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

// ---------- Overview (hero stats + top sites) ----------
export const getNodeOverview = (nodeId) => request(`/nodes/${nodeId}/overview`);

// ---------- Telemetry (read-only, each with a "latest" + most a "/history") ----------
export const getOsInfo = (nodeId) => request(`/nodes/${nodeId}/os-info`);
export const getHardwareInfo = (nodeId) => request(`/nodes/${nodeId}/hardware-info`);

export const getLatestCpu = (nodeId) => request(`/nodes/${nodeId}/cpu`);
export const getCpuHistory = (nodeId, limit = 60) => request(`/nodes/${nodeId}/cpu/history?limit=${limit}`);

export const getLatestRam = (nodeId) => request(`/nodes/${nodeId}/ram`);
export const getRamHistory = (nodeId, limit = 60) => request(`/nodes/${nodeId}/ram/history?limit=${limit}`);

export const getLatestDisk = (nodeId) => request(`/nodes/${nodeId}/disk`);
export const getDiskHistory = (nodeId, limit = 60) => request(`/nodes/${nodeId}/disk/history?limit=${limit}`);

export const getLatestNetworkIo = (nodeId) => request(`/nodes/${nodeId}/network-io`);
export const getNetworkIoHistory = (nodeId, limit = 60) => request(`/nodes/${nodeId}/network-io/history?limit=${limit}`);

export const getProcessHistory = (nodeId, limit = 15, offset = 0) =>
  request(`/nodes/${nodeId}/processes/history?limit=${limit}&offset=${offset}`);

export const getActiveConnections = (nodeId, limit = 15, offset = 0) =>
  request(`/nodes/${nodeId}/active-connections?limit=${limit}&offset=${offset}`);

export const getSystemLogs = (nodeId) => request(`/nodes/${nodeId}/system-logs`);
export const getAuthEvents = (nodeId) => request(`/nodes/${nodeId}/auth-events`);

export const getBrowserHistory = (nodeId) => request(`/nodes/${nodeId}/browser-history`);

export const getNetworkConfig = (nodeId) => request(`/nodes/${nodeId}/network-config`);

export const getSecurityStatus = (nodeId) => request(`/nodes/${nodeId}/security-status`);
export const getSecurityStatusHistory = (nodeId, limit = 48) => request(`/nodes/${nodeId}/security-status/history?limit=${limit}`);

export const getInstalledPackages = (nodeId) => request(`/nodes/${nodeId}/installed-packages`);

// ---------- Firewall Rules (full CRUD) ----------
export const getFirewallRules = (nodeId) => request(`/nodes/${nodeId}/firewall-rules`);
export const getFirewallRule = (nodeId, ruleId) => request(`/nodes/${nodeId}/firewall-rules/${ruleId}`);
export const createFirewallRule = (nodeId, rule) =>
  request(`/nodes/${nodeId}/firewall-rules`, { method: 'POST', body: rule });
export const updateFirewallRule = (nodeId, ruleId, rule) =>
  request(`/nodes/${nodeId}/firewall-rules/${ruleId}`, { method: 'PUT', body: rule });
export const deleteFirewallRule = (nodeId, ruleId) =>
  request(`/nodes/${nodeId}/firewall-rules/${ruleId}`, { method: 'DELETE' });
export const getFirewallStatus = (nodeId) => request(`/nodes/${nodeId}/firewall-status`);
export const getFirewallHistory = (nodeId, limit = 100) =>
  request(`/nodes/${nodeId}/firewall-history?limit=${limit}`);

// ---------- Commands (create + manage) ----------
export const getCommands = (nodeId, limit = 20) => request(`/nodes/${nodeId}/commands?limit=${limit}`);
export const getCommand = (nodeId, commandId) => request(`/nodes/${nodeId}/commands/${commandId}`);
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

// ---------- Anomalies ----------
export const runAnomalyScan = (nodeId, hours = 6) =>
  request(`/nodes/${nodeId}/anomaly-scan?hours=${hours}`, { method: 'POST' });
export const getAnomalies = (nodeId, includeDismissed = false, limit = 50) =>
  request(`/nodes/${nodeId}/anomalies?include_dismissed=${includeDismissed}&limit=${limit}`);
export const dismissAnomaly = (nodeId, anomalyId) =>
  request(`/nodes/${nodeId}/anomalies/${anomalyId}/dismiss`, { method: 'PATCH' });

export { BASE_URL };