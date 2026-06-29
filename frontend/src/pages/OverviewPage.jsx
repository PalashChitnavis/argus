import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getNodeOverview } from '../api/client';
import StatusPill from '../components/StatusPill';

function pct(n, digits = 1) {
  return n === null || n === undefined ? null : Number(n).toFixed(digits);
}

function usageTone(percent) {
  if (percent === null || percent === undefined) return '';
  if (percent >= 85) return 'red';
  if (percent >= 60) return 'amber';
  return 'green';
}

function timeAgo(unixSeconds) {
  if (!unixSeconds) return null;
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatBytes(mb) {
  if (mb === null || mb === undefined) return '—';
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
  return `${mb.toFixed(1)} MB`;
}

export default function OverviewPage() {
  const { nodeId } = useParams();
  const { data, loading, error, reload } = useFetch(() => getNodeOverview(nodeId), [nodeId]);

  if (loading) return <div className="loading-text">Loading overview…</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return null;

  const { node, os_info, hardware_info, latest_cpu, latest_ram, latest_disk, latest_network_io, latest_security, top_domains, active_connection_count, process_count_last_hour } = data;

  const cpuPct = pct(latest_cpu?.cpu_percent_used);
  const ramPct = pct(latest_ram?.ram_percent_used);
  const diskPct = pct(latest_disk?.disk_percent_used);

  const securityChecks = latest_security ? [
    { label: 'Firewall', ok: latest_security.firewall_active, detail: latest_security.firewall_tool || 'none detected' },
    { label: 'Disk encryption', ok: latest_security.disk_encrypted, detail: latest_security.disk_encrypted ? 'LUKS enabled' : 'not encrypted' },
    { label: 'Root login', ok: !latest_security.root_login_permitted, detail: latest_security.root_login_permitted ? 'permitted over SSH' : 'blocked' },
    { label: 'Password auth', ok: !latest_security.password_auth_permitted, detail: latest_security.password_auth_permitted ? 'enabled' : 'disabled (key-only)' },
  ] : [];
  const securityIssueCount = securityChecks.filter((c) => c.ok === false).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">
            {node.hostname || node.machine_id} <StatusPill status={node.status} />
          </div>
          <div className="page-sub mono">{node.machine_id}</div>
        </div>
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      {/* ---- Hero stats: the 3-4 most important numbers, large ---- */}
      <div className="grid grid-4 section">
        <div className="panel">
          <div className="panel-title">CPU</div>
          <div className={`stat-value ${usageTone(Number(cpuPct))}`}>{cpuPct !== null ? `${cpuPct}%` : '—'}</div>
          <div className="stat-label">{hardware_info ? `${hardware_info.cpu_cores_physical} cores / ${hardware_info.cpu_cores_logical} threads` : 'no data yet'}</div>
        </div>
        <div className="panel">
          <div className="panel-title">Memory</div>
          <div className={`stat-value ${usageTone(Number(ramPct))}`}>{ramPct !== null ? `${ramPct}%` : '—'}</div>
          <div className="stat-label">
            {latest_ram ? `${pct(latest_ram.ram_used_gb)} / ${hardware_info ? hardware_info.ram_total_gb : '?'} GB used` : 'no data yet'}
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">Disk</div>
          <div className={`stat-value ${usageTone(Number(diskPct))}`}>{diskPct !== null ? `${diskPct}%` : '—'}</div>
          <div className="stat-label">
            {latest_disk ? `${pct(latest_disk.disk_used_gb)} / ${hardware_info ? hardware_info.disk_total_gb : '?'} GB used` : 'no data yet'}
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">Security</div>
          <div className={`stat-value ${securityIssueCount === 0 ? 'green' : 'amber'}`}>
            {latest_security ? (securityIssueCount === 0 ? 'Good' : `${securityIssueCount} issue${securityIssueCount > 1 ? 's' : ''}`) : '—'}
          </div>
          <div className="stat-label">{latest_security ? 'tap Telemetry for details' : 'no data yet'}</div>
        </div>
      </div>

      <div className="grid grid-2 section">
        {/* ---- System identity ---- */}
        <div className="panel">
          <div className="panel-title">This machine</div>
          {os_info ? (
            <>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>
                {os_info.distro_name} {os_info.distro_version}
              </div>
              <div className="text-dim mono" style={{ fontSize: 12 }}>
                kernel {os_info.kernel_version} · {os_info.architecture}
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 18 }}>
                <div>
                  <div className="stat-label" style={{ marginBottom: 2 }}>CPU</div>
                  <div className="mono" style={{ fontSize: 13 }}>{hardware_info?.cpu_cores_physical ?? '?'} cores</div>
                </div>
                <div>
                  <div className="stat-label" style={{ marginBottom: 2 }}>RAM</div>
                  <div className="mono" style={{ fontSize: 13 }}>{hardware_info?.ram_total_gb ?? '?'} GB</div>
                </div>
                <div>
                  <div className="stat-label" style={{ marginBottom: 2 }}>Disk</div>
                  <div className="mono" style={{ fontSize: 13 }}>{hardware_info?.disk_total_gb ?? '?'} GB</div>
                </div>
              </div>
            </>
          ) : (
            <div className="muted">No system info received yet — waiting for the agent's startup report.</div>
          )}
        </div>

        {/* ---- Network snapshot — eye-catching #1 ---- */}
        <div className="panel">
          <div className="panel-title">Network right now</div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'baseline' }}>
            <div>
              <div className="stat-value" style={{ fontSize: 22 }}>{active_connection_count}</div>
              <div className="stat-label">active connections</div>
            </div>
            <div>
              <div className="stat-value" style={{ fontSize: 22 }}>{process_count_last_hour}</div>
              <div className="stat-label">new processes (1h)</div>
            </div>
          </div>
          {latest_network_io && (
            <div className="text-dim" style={{ fontSize: 12, marginTop: 10 }}>
              ↑ {formatBytes(latest_network_io.bytes_sent_mb)} sent · ↓ {formatBytes(latest_network_io.bytes_recv_mb)} received (cumulative since boot)
            </div>
          )}
        </div>
      </div>

      {/* ---- Most visited sites — eye-catching #2 ---- */}
      <div className="section">
        <div className="section-title">Most visited sites</div>
        <div className="table-wrap">
          {(!top_domains || top_domains.length === 0) ? (
            <div className="empty-state">No browser history collected yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Visits</th>
                  <th>Last visited</th>
                </tr>
              </thead>
              <tbody>
                {top_domains.map((d) => (
                  <tr key={d.domain}>
                    <td className="mono">{d.domain}</td>
                    <td>
                      <span className="badge" style={{ color: 'var(--text)' }}>{d.visit_count}</span>
                    </td>
                    <td className="text-dim">{timeAgo(d.last_visit_time) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
