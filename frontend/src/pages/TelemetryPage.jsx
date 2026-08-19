import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import {
  getHardwareInfo,
  getLatestCpu,
  getCpuHistory,
  getLatestRam,
  getLatestDisk,
  getLatestNetworkIo,
  getProcessHistory,
  getActiveConnections,
  getSystemLogs,
  getAuthEvents,
  getBrowserHistory,
  getNetworkConfig,
  getSecurityStatus,
  getInstalledPackages,
} from '../api/client';
import RefreshButton from '../components/RefreshButton';
import Pagination from '../components/Pagination';

const PAGE_SIZE = 15;

function fmt(v, digits = 1) {
  return v === null || v === undefined ? '—' : Number(v).toFixed(digits);
}

function timeAgo(unixSeconds) {
  if (!unixSeconds) return '—';
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function relativeTime(iso) {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function SectionHeader({ title, subtitle, lastUpdated, nodeId, collector, onResult }) {
  return (
    <div className="section-title">
      <span>
        {title}
        {subtitle && <span className="text-dim" style={{ fontWeight: 400, fontSize: 12, marginLeft: 8 }}>{subtitle}</span>}
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {lastUpdated && <span className="muted" style={{ fontSize: 11.5 }}>updated {lastUpdated}</span>}
        <RefreshButton nodeId={nodeId} collector={collector} onResult={onResult} />
      </span>
    </div>
  );
}

// ── CPU ───────────────────────────────────────────────────────────────────────

function CpuSection({ nodeId }) {
  console.log('CpuSection rendered');
  const { data, loading, error, reload } = useFetch(() => getLatestCpu(nodeId), [nodeId]);
  const { data: history } = useFetch(() => getCpuHistory(nodeId, 20), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="CPU usage"
        subtitle="collected every minute"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="cpu"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : (
        <div className="grid grid-2">
          <div className="panel">
            <div className="panel-title">Current</div>
            <div className={`stat-value ${data?.cpu_percent_used > 80 ? 'red' : data?.cpu_percent_used > 60 ? 'amber' : 'green'}`}>
              {data ? `${fmt(data.cpu_percent_used)}%` : 'no data yet'}
            </div>
          </div>
          <div className="panel">
            <div className="panel-title">Last 20 readings</div>
            {!history || history.length === 0 ? (
              <div className="muted" style={{ fontSize: 12.5 }}>No history yet</div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 40 }}>
                {[...history].reverse().map((h, i) => (
                  <div
                    key={i}
                    title={`${fmt(h.cpu_percent_used)}% at ${new Date(h.received_at).toLocaleTimeString()}`}
                    style={{
                      flex: 1,
                      height: `${Math.max(4, Math.min(100, h.cpu_percent_used || 0))}%`,
                      background: (h.cpu_percent_used || 0) > 80 ? 'var(--red)' : (h.cpu_percent_used || 0) > 60 ? 'var(--amber)' : 'var(--green)',
                      borderRadius: 1,
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── RAM ───────────────────────────────────────────────────────────────────────

function RamSection({ nodeId, ramTotalGb }) {
  const { data, loading, error, reload } = useFetch(() => getLatestRam(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="Memory usage"
        subtitle="collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="ram"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No memory data yet.</div>
      ) : (
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="text-dim" style={{ fontSize: 13 }}>
              {fmt(data.ram_used_gb)} GB used of {ramTotalGb ?? '?'} GB
            </span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{fmt(data.ram_percent_used)}%</span>
          </div>
          <div style={{ background: 'var(--bg)', borderRadius: 4, height: 8, overflow: 'hidden', border: '1px solid var(--border-bright)' }}>
            <div
              style={{
                width: `${Math.min(100, data.ram_percent_used || 0)}%`,
                height: '100%',
                background: data.ram_percent_used > 85 ? 'var(--red)' : data.ram_percent_used > 60 ? 'var(--amber)' : 'var(--green)',
              }}
            />
          </div>
          <div className="text-dim" style={{ fontSize: 12, marginTop: 8 }}>{fmt(data.ram_available_gb)} GB available</div>
        </div>
      )}
    </div>
  );
}

// ── Disk ──────────────────────────────────────────────────────────────────────

function DiskSection({ nodeId, diskTotalGb }) {
  const { data, loading, error, reload } = useFetch(() => getLatestDisk(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="Disk usage"
        subtitle="collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="disk"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No disk data yet.</div>
      ) : (
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="text-dim" style={{ fontSize: 13 }}>
              {fmt(data.disk_used_gb)} GB used of {diskTotalGb ?? '?'} GB
            </span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{fmt(data.disk_percent_used)}%</span>
          </div>
          <div style={{ background: 'var(--bg)', borderRadius: 4, height: 8, overflow: 'hidden', border: '1px solid var(--border-bright)' }}>
            <div
              style={{
                width: `${Math.min(100, data.disk_percent_used || 0)}%`,
                height: '100%',
                background: data.disk_percent_used > 90 ? 'var(--red)' : data.disk_percent_used > 75 ? 'var(--amber)' : 'var(--green)',
              }}
            />
          </div>
          <div className="text-dim" style={{ fontSize: 12, marginTop: 8 }}>{fmt(data.disk_free_gb)} GB free</div>
        </div>
      )}
    </div>
  );
}

// ── Network I/O ───────────────────────────────────────────────────────────────

function NetworkIoSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getLatestNetworkIo(nodeId), [nodeId]);

  function formatMb(mb) {
    if (mb === null || mb === undefined) return '—';
    return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`;
  }

  return (
    <div className="section">
      <SectionHeader
        title="Network traffic"
        subtitle="cumulative since boot, collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="network_io"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No network data yet.</div>
      ) : (
        <div className="grid grid-2">
          <div className="panel">
            <div className="panel-title">Sent</div>
            <div className="stat-value" style={{ fontSize: 20 }}>↑ {formatMb(data.bytes_sent_mb)}</div>
          </div>
          <div className="panel">
            <div className="panel-title">Received</div>
            <div className="stat-value" style={{ fontSize: 20 }}>↓ {formatMb(data.bytes_recv_mb)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Processes ─────────────────────────────────────────────────────────────────

function ProcessesSection({ nodeId }) {
  const [offset, setOffset] = useState(0);
  const { data, loading, error, reload } = useFetch(
    () => getProcessHistory(nodeId, PAGE_SIZE, offset),
    [nodeId, offset]
  );

  return (
    <div className="section">
      <SectionHeader
        title="Recently started processes"
        subtitle="new processes seen since the last check, every minute"
        nodeId={nodeId}
        collector="processes"
        onResult={() => { setOffset(0); reload(); }}
      />
      {error && <div className="error-banner">{error}</div>}
      <div className="table-wrap">
        {loading ? (
          <div className="loading-text">Loading…</div>
        ) : !data || data.items.length === 0 ? (
          <div className="empty-state">No new processes detected recently.</div>
        ) : (
          <table>
            <thead>
              <tr><th>Process</th><th>User</th><th>CPU</th><th>Memory</th><th>Started</th></tr>
            </thead>
            <tbody>
              {data.items.map((p, i) => (
                <tr key={i}>
                  <td className="mono">{p.name || '—'} <span className="text-dim">({p.pid})</span></td>
                  <td className="text-dim">{p.username || '—'}</td>
                  <td>{fmt(p.cpu_percent)}%</td>
                  <td>{fmt(p.memory_percent)}%</td>
                  <td className="text-dim">{relativeTime(p.received_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {data && (
        <Pagination total={data.total} limit={data.limit} offset={data.offset} onPageChange={setOffset} />
      )}
    </div>
  );
}

// ── Active connections ───────────────────────────────────────────────────────

function ConnectionsSection({ nodeId }) {
  const [offset, setOffset] = useState(0);
  const { data, loading, error, reload } = useFetch(
    () => getActiveConnections(nodeId, PAGE_SIZE, offset),
    [nodeId, offset]
  );

  return (
    <div className="section">
      <SectionHeader
        title="Active network connections"
        subtitle="snapshot, collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="active_connections"
        onResult={() => { setOffset(0); reload(); }}
      />
      {error && <div className="error-banner">{error}</div>}
      <div className="table-wrap">
        {loading ? (
          <div className="loading-text">Loading…</div>
        ) : !data || data.connections.length === 0 ? (
          <div className="empty-state">No active connections captured yet.</div>
        ) : (
          <table>
            <thead>
              <tr><th>Local</th><th>Remote</th><th>Status</th><th>Process</th></tr>
            </thead>
            <tbody>
              {data.connections.map((c, i) => (
                <tr key={i}>
                  <td className="mono">{c.local_ip}:{c.local_port}</td>
                  <td className="mono">{c.remote_ip ? `${c.remote_ip}:${c.remote_port}` : 'listening'}</td>
                  <td><span className="badge">{c.status}</span></td>
                  <td className="text-dim">{c.process_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {data && (
        <Pagination total={data.total} limit={data.limit} offset={data.offset} onPageChange={setOffset} />
      )}
    </div>
  );
}

// ── Browser history ───────────────────────────────────────────────────────────

function BrowserHistorySection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getBrowserHistory(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="Browsing activity"
        subtitle="collected every 10 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="browser_history"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No browser history collected yet.</div>
      ) : (
        <div className="grid grid-2">
          <div>
            <div className="panel-title" style={{ marginBottom: 8 }}>Most visited domains</div>
            <div className="table-wrap">
              {data.most_visited.length === 0 ? (
                <div className="empty-state">None</div>
              ) : (
                <table>
                  <thead><tr><th>Domain</th><th>Visits</th></tr></thead>
                  <tbody>
                    {data.most_visited.slice(0, 8).map((d) => (
                      <tr key={d.domain}>
                        <td className="mono">{d.domain}</td>
                        <td>{d.visit_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
          <div>
            <div className="panel-title" style={{ marginBottom: 8 }}>Recently visited</div>
            <div className="table-wrap">
              {data.recently_visited.length === 0 ? (
                <div className="empty-state">None</div>
              ) : (
                <table>
                  <thead><tr><th>Site</th><th>When</th></tr></thead>
                  <tbody>
                    {data.recently_visited.slice(0, 8).map((d, i) => (
                      <tr key={i}>
                        <td className="mono">{d.domain}</td>
                        <td className="text-dim">{timeAgo(d.last_visit_time)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Network config ────────────────────────────────────────────────────────────

function NetworkConfigSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getNetworkConfig(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="Network configuration"
        subtitle="interfaces, DNS, routing — collected every 30 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="network_interfaces"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No network configuration collected yet.</div>
      ) : (
        <div className="grid grid-2">
          <div className="panel">
            <div className="panel-title">Interfaces</div>
            {data.interfaces.map((iface, i) => (
              <div key={i} style={{ marginBottom: 8, fontSize: 12.5 }}>
                <div className="mono" style={{ fontWeight: 600 }}>{iface.interface_name}</div>
                <div className="text-dim">{iface.ipv4 || 'no IPv4'} {iface.mac_address && `· ${iface.mac_address}`}</div>
              </div>
            ))}
          </div>
          <div className="panel">
            <div className="panel-title">DNS servers</div>
            <div className="mono" style={{ fontSize: 13 }}>{data.dns_servers.join(', ') || 'none'}</div>
            <div className="panel-title" style={{ marginTop: 14 }}>Default route</div>
            <div className="mono text-dim" style={{ fontSize: 12 }}>{data.routing_table[0] || '—'}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Security ──────────────────────────────────────────────────────────────────

function SecuritySection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getSecurityStatus(nodeId), [nodeId]);

  const checks = data ? [
    { label: 'Firewall active', ok: data.firewall_active, good: 'Active', bad: 'Inactive', detail: data.firewall_tool },
    { label: 'Disk encryption', ok: data.disk_encrypted, good: 'Encrypted', bad: 'Not encrypted' },
    { label: 'Root SSH login', ok: !data.root_login_permitted, good: 'Blocked', bad: 'Permitted' },
    { label: 'Password SSH auth', ok: !data.password_auth_permitted, good: 'Disabled', bad: 'Enabled' },
    { label: 'Mandatory access control', ok: data.mac_enabled, good: 'Enforcing', bad: 'Not enforcing', detail: data.mac_tool },
  ] : [];

  return (
    <div className="section">
      <SectionHeader
        title="Security posture"
        subtitle="collected every 30 minutes"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="security_status"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No security data collected yet.</div>
      ) : (
        <div className="grid grid-3">
          {checks.map((c) => (
            <div className="panel" key={c.label}>
              <div className="panel-title">{c.label}</div>
              <div className={`stat-value ${c.ok === null ? '' : c.ok ? 'green' : 'red'}`} style={{ fontSize: 18 }}>
                {c.ok === null ? 'Unknown' : c.ok ? c.good : c.bad}
              </div>
              {c.detail && <div className="text-dim" style={{ fontSize: 12, marginTop: 2 }}>{c.detail}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Logs ──────────────────────────────────────────────────────────────────────

function LogsSection({ nodeId }) {
  const { data: sysLogs, loading: l1, reload: r1 } = useFetch(() => getSystemLogs(nodeId), [nodeId]);
  const { data: authLogs, loading: l2, reload: r2 } = useFetch(() => getAuthEvents(nodeId), [nodeId]);

  return (
    <div className="section">
      <div className="section-title">
        <span>System &amp; auth activity <span className="text-dim" style={{ fontWeight: 400, fontSize: 12, marginLeft: 8 }}>collected every 5 minutes</span></span>
        <span style={{ display: 'flex', gap: 8 }}>
          <RefreshButton nodeId={nodeId} collector="system_logs" onResult={() => r1()} />
          <RefreshButton nodeId={nodeId} collector="auth_events" onResult={() => r2()} />
        </span>
      </div>
      <div className="grid grid-2">
        <div>
          <div className="panel-title" style={{ marginBottom: 8 }}>System log (recent)</div>
          <div className="table-wrap" style={{ maxHeight: 220, overflowY: 'auto' }}>
            {l1 ? (
              <div className="loading-text">Loading…</div>
            ) : !sysLogs || sysLogs.log_lines.length === 0 ? (
              <div className="empty-state">No recent system log lines.</div>
            ) : (
              <div className="json-cell" style={{ padding: 12 }}>
                {sysLogs.log_lines.slice(0, 12).join('\n')}
              </div>
            )}
          </div>
        </div>
        <div>
          <div className="panel-title" style={{ marginBottom: 8 }}>Authentication events</div>
          <div className="table-wrap" style={{ maxHeight: 220, overflowY: 'auto' }}>
            {l2 ? (
              <div className="loading-text">Loading…</div>
            ) : !authLogs || authLogs.log_lines.length === 0 ? (
              <div className="empty-state">No recent auth events.</div>
            ) : (
              <div className="json-cell" style={{ padding: 12 }}>
                {authLogs.log_lines.slice(0, 12).join('\n')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Installed packages ───────────────────────────────────────────────────────

function PackagesSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getInstalledPackages(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader
        title="Installed packages"
        subtitle="collected once daily"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId}
        collector="installed_packages"
        onResult={() => reload()}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? (
        <div className="loading-text">Loading…</div>
      ) : !data ? (
        <div className="empty-state">No package list collected yet.</div>
      ) : (
        <div className="panel">
          <div className="text-dim" style={{ fontSize: 12.5, marginBottom: 8 }}>{data.packages.length} packages installed</div>
          <div className="mono text-dim" style={{ fontSize: 11.5, maxHeight: 100, overflowY: 'auto', lineHeight: 1.7 }}>
            {data.packages.slice(0, 60).join(', ')}{data.packages.length > 60 ? '…' : ''}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TelemetryPage() {
  const { nodeId } = useParams();
  const { data: hardwareInfo } = useFetch(() => getHardwareInfo(nodeId), [nodeId]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Telemetry</div>
          <div className="page-sub">Everything the agent has reported, formatted for reading — refresh any section to pull live data from the node.</div>
        </div>
      </div>

      <CpuSection nodeId={nodeId} />
      <RamSection nodeId={nodeId} ramTotalGb={hardwareInfo?.ram_total_gb} />
      <DiskSection nodeId={nodeId} diskTotalGb={hardwareInfo?.disk_total_gb} />
      <NetworkIoSection nodeId={nodeId} />
      <ProcessesSection nodeId={nodeId} />
      <ConnectionsSection nodeId={nodeId} />
      <BrowserHistorySection nodeId={nodeId} />
      <NetworkConfigSection nodeId={nodeId} />
      <SecuritySection nodeId={nodeId} />
      <LogsSection nodeId={nodeId} />
      <PackagesSection nodeId={nodeId} />
    </div>
  );
}