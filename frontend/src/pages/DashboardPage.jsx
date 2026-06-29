import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getNodeDashboard } from '../api/client';
import StatusPill from '../components/StatusPill';

function Stat({ label, value, suffix = '', tone }) {
  return (
    <div className="panel">
      <div className="panel-title">{label}</div>
      <div className={`stat-value ${tone || ''}`}>
        {value === null || value === undefined ? '—' : value}
        {value !== null && value !== undefined ? suffix : ''}
      </div>
    </div>
  );
}

function pct(n) {
  return n === null || n === undefined ? null : Number(n).toFixed(1);
}

export default function DashboardPage() {
  const { nodeId } = useParams();
  const { data, loading, error, reload } = useFetch(() => getNodeDashboard(nodeId), [nodeId]);

  if (loading) return <div className="loading-text">Loading dashboard…</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return null;

  const { node, one_minute_data, five_minute_data, thirty_minute_data, startup_data } = data;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">
            {node.hostname} <StatusPill status={node.status} />
          </div>
          <div className="page-sub mono">{node.machine_id}</div>
        </div>
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      <div className="section">
        <div className="section-title">Live metrics</div>
        <div className="grid grid-4">
          <Stat
            label="CPU usage"
            value={pct(one_minute_data?.cpu_percent_used)}
            suffix="%"
            tone={one_minute_data?.cpu_percent_used > 80 ? 'red' : 'green'}
          />
          <Stat
            label="RAM usage"
            value={pct(five_minute_data?.ram_percent_used)}
            suffix="%"
            tone={five_minute_data?.ram_percent_used > 80 ? 'red' : 'green'}
          />
          <Stat
            label="Disk usage"
            value={pct(five_minute_data?.disk_percent_used)}
            suffix="%"
            tone={five_minute_data?.disk_percent_used > 85 ? 'red' : 'green'}
          />
          <Stat
            label="Firewall"
            value={thirty_minute_data?.firewall_active === undefined ? '—' : (thirty_minute_data?.firewall_active ? 'Active' : 'Inactive')}
            tone={thirty_minute_data?.firewall_active ? 'green' : 'amber'}
          />
        </div>
      </div>

      <div className="section">
        <div className="section-title">System profile</div>
        <div className="grid grid-3">
          <div className="panel">
            <div className="panel-title">OS</div>
            <div className="mono" style={{ fontSize: 13 }}>
              {startup_data?.distro_name} {startup_data?.distro_version}
            </div>
            <div className="text-dim" style={{ fontSize: 12, marginTop: 4 }}>
              kernel {startup_data?.kernel_version} · {startup_data?.architecture}
            </div>
          </div>
          <div className="panel">
            <div className="panel-title">CPU / RAM</div>
            <div className="mono" style={{ fontSize: 13 }}>
              {startup_data?.cpu_cores_physical} cores / {startup_data?.cpu_cores_logical} threads
            </div>
            <div className="text-dim" style={{ fontSize: 12, marginTop: 4 }}>
              {startup_data?.ram_total_gb} GB RAM · {startup_data?.disk_total_gb} GB disk
            </div>
          </div>
          <div className="panel">
            <div className="panel-title">Security posture</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 2 }}>
              <span className={`badge ${thirty_minute_data?.disk_encrypted ? 'allow' : 'deny'}`}>
                disk {thirty_minute_data?.disk_encrypted ? 'encrypted' : 'unencrypted'}
              </span>
              <span className={`badge ${thirty_minute_data?.root_login_permitted ? 'deny' : 'allow'}`}>
                root login {thirty_minute_data?.root_login_permitted ? 'allowed' : 'blocked'}
              </span>
              <span className={`badge ${thirty_minute_data?.password_auth_permitted ? 'deny' : 'allow'}`}>
                password auth {thirty_minute_data?.password_auth_permitted ? 'on' : 'off'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="section">
        <div className="section-title">Recent network connections</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Local</th>
                <th>Remote</th>
                <th>Status</th>
                <th>Process</th>
              </tr>
            </thead>
            <tbody>
              {(!five_minute_data?.connections || five_minute_data.connections.length === 0) && (
                <tr className="empty-row"><td colSpan={4}>No connection data yet</td></tr>
              )}
              {five_minute_data?.connections?.slice(0, 8).map((c, i) => (
                <tr key={i}>
                  <td className="mono">{c.local_ip}:{c.local_port}</td>
                  <td className="mono">{c.remote_ip}:{c.remote_port}</td>
                  <td><span className="badge">{c.status}</span></td>
                  <td className="text-dim">{c.process_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
