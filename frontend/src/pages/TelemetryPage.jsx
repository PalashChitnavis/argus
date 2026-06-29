import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import {
  getOneMinuteDataHistory,
  getFiveMinuteDataHistory,
  getThirtyMinuteDataHistory,
  getDailyDataHistory,
  getStartupDataHistory,
} from '../api/client';

const TABS = [
  { key: 'one', label: '1-Minute (CPU/Procs)' },
  { key: 'five', label: '5-Minute (Disk/Net)' },
  { key: 'thirty', label: '30-Minute (Security)' },
  { key: 'daily', label: 'Daily' },
  { key: 'startup', label: 'Startup' },
];

function fmt(v, digits = 1) {
  return v === null || v === undefined ? '—' : Number(v).toFixed(digits);
}

function OneMinuteTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Received</th><th>CPU %</th><th>New processes</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr className="empty-row"><td colSpan={3}>No data yet</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-dim">{new Date(r.received_at).toLocaleString()}</td>
              <td className="mono">{fmt(r.cpu_percent_used)}%</td>
              <td className="json-cell">
                {r.new_processes?.length
                  ? r.new_processes.map((p) => `${p.name} (pid ${p.pid}, ${fmt(p.cpu_percent)}% cpu)`).join('\n')
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FiveMinuteTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Received</th><th>Disk</th><th>RAM</th><th>Net I/O (MB)</th><th>Connections</th><th>Auth events</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr className="empty-row"><td colSpan={6}>No data yet</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-dim">{new Date(r.received_at).toLocaleString()}</td>
              <td className="mono">{fmt(r.disk_percent_used)}% ({fmt(r.disk_used_gb)}/{fmt(r.disk_used_gb + r.disk_free_gb)} GB)</td>
              <td className="mono">{fmt(r.ram_percent_used)}%</td>
              <td className="mono">↑{fmt(r.bytes_sent_mb)} ↓{fmt(r.bytes_recv_mb)}</td>
              <td>{r.connections?.length ?? 0}</td>
              <td>{r.auth_events?.length ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ThirtyMinuteTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Received</th><th>Firewall</th><th>Disk encrypted</th><th>Root login</th><th>Password auth</th><th>Interfaces</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr className="empty-row"><td colSpan={6}>No data yet</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-dim">{new Date(r.received_at).toLocaleString()}</td>
              <td><span className={`badge ${r.firewall_active ? 'allow' : 'deny'}`}>{r.firewall_tool || 'unknown'} {r.firewall_active ? 'active' : 'inactive'}</span></td>
              <td><span className={`badge ${r.disk_encrypted ? 'allow' : 'deny'}`}>{r.disk_encrypted ? 'yes' : 'no'}</span></td>
              <td><span className={`badge ${r.root_login_permitted ? 'deny' : 'allow'}`}>{r.root_login_permitted ? 'allowed' : 'blocked'}</span></td>
              <td><span className={`badge ${r.password_auth_permitted ? 'deny' : 'allow'}`}>{r.password_auth_permitted ? 'on' : 'off'}</span></td>
              <td className="text-dim">{r.interfaces?.map((i) => i.interface_name).join(', ') || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DailyTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Received</th><th>Distro</th><th>Kernel</th><th>CPU</th><th>RAM</th><th>Disk</th><th>Packages</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr className="empty-row"><td colSpan={7}>No data yet</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-dim">{new Date(r.received_at).toLocaleString()}</td>
              <td className="mono">{r.distro_name} {r.distro_version}</td>
              <td className="mono text-dim">{r.kernel_version}</td>
              <td>{r.cpu_cores_physical}/{r.cpu_cores_logical}</td>
              <td>{fmt(r.ram_total_gb)} GB</td>
              <td>{fmt(r.disk_total_gb)} GB</td>
              <td>{r.packages?.length ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StartupTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Received</th><th>Distro</th><th>Kernel</th><th>Arch</th><th>CPU</th><th>RAM</th><th>Disk</th><th>Packages</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr className="empty-row"><td colSpan={8}>No data yet</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="text-dim">{new Date(r.received_at).toLocaleString()}</td>
              <td className="mono">{r.distro_name} {r.distro_version}</td>
              <td className="mono text-dim">{r.kernel_version}</td>
              <td>{r.architecture}</td>
              <td>{r.cpu_cores_physical}/{r.cpu_cores_logical}</td>
              <td>{fmt(r.ram_total_gb)} GB</td>
              <td>{fmt(r.disk_total_gb)} GB</td>
              <td>{r.packages?.length ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TelemetryPage() {
  const { nodeId } = useParams();
  const [tab, setTab] = useState('one');

  const fetchers = {
    one: () => getOneMinuteDataHistory(nodeId, 60),
    five: () => getFiveMinuteDataHistory(nodeId, 60),
    thirty: () => getThirtyMinuteDataHistory(nodeId, 48),
    daily: () => getDailyDataHistory(nodeId, 30),
    startup: () => getStartupDataHistory(nodeId, 10),
  };

  const { data, loading, error, reload } = useFetch(fetchers[tab], [nodeId, tab]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Telemetry</div>
          <div className="page-sub">Historical data collected from this node</div>
        </div>
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <div key={t.key} className={`tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
            {t.label}
          </div>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading…</div>}

      {!loading && !error && data && (
        <>
          {tab === 'one' && <OneMinuteTable rows={data} />}
          {tab === 'five' && <FiveMinuteTable rows={data} />}
          {tab === 'thirty' && <ThirtyMinuteTable rows={data} />}
          {tab === 'daily' && <DailyTable rows={data} />}
          {tab === 'startup' && <StartupTable rows={data} />}
        </>
      )}
    </div>
  );
}
