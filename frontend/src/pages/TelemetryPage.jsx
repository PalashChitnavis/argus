import { useState, useEffect } from 'react';
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

// ─── helpers ──────────────────────────────────────────────────────────────────

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

function cpuColor(v) {
  return v > 80 ? 'var(--red)' : v > 60 ? 'var(--amber)' : 'var(--green)';
}

// ─── Pagination ─────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

function Pagination({ page, setPage, total, pageSize = PAGE_SIZE }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (pageCount <= 1) return null;

  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  const btnStyle = (disabled) => ({
    padding: '2px 10px',
    borderRadius: 4,
    fontSize: 11.5,
    border: '1px solid var(--border)',
    background: 'transparent',
    color: disabled ? 'var(--text-faint)' : 'var(--text-dim)',
    cursor: disabled ? 'default' : 'pointer',
    fontFamily: 'var(--sans)',
  });

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, justifyContent: 'flex-end' }}>
      <span className="text-dim" style={{ fontSize: 11.5 }}>
        {start}–{end} of {total}
      </span>
      <button style={btnStyle(page === 1)} disabled={page === 1} onClick={() => setPage(1)}>«</button>
      <button style={btnStyle(page === 1)} disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹ Prev</button>
      <span className="text-dim" style={{ fontSize: 11.5 }}>Page {page} / {pageCount}</span>
      <button style={btnStyle(page === pageCount)} disabled={page === pageCount} onClick={() => setPage(p => Math.min(pageCount, p + 1))}>Next ›</button>
      <button style={btnStyle(page === pageCount)} disabled={page === pageCount} onClick={() => setPage(pageCount)}>»</button>
    </div>
  );
}

function SectionHeader({ title, subtitle, lastUpdated, nodeId, collector, onResult, extra }) {
  return (
    <div className="section-title">
      <span>
        {title}
        {subtitle && <span className="text-dim" style={{ fontWeight: 400, fontSize: 12, marginLeft: 8 }}>{subtitle}</span>}
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {extra}
        {lastUpdated && <span className="muted" style={{ fontSize: 11.5 }}>updated {lastUpdated}</span>}
        <RefreshButton nodeId={nodeId} collector={collector} onResult={onResult} />
      </span>
    </div>
  );
}

// ─── CPU ──────────────────────────────────────────────────────────────────────

function CpuSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getLatestCpu(nodeId), [nodeId]);
  const { data: history } = useFetch(() => getCpuHistory(nodeId, 20), [nodeId]);

  const vals = history ? [...history].reverse().map(h => h.cpu_percent_used || 0) : [];
  const maxVal = vals.length ? Math.max(...vals) : 0;
  const minVal = vals.length ? Math.min(...vals) : 0;
  const avgVal = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;

  return (
    <div className="section">
      <SectionHeader
        title="CPU usage"
        subtitle="collected every minute"
        lastUpdated={data && relativeTime(data.received_at)}
        nodeId={nodeId} collector="cpu" onResult={reload}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div> : (
        <div className="grid grid-2">
          <div className="panel">
            <div className="panel-title">Current</div>
            <div className="stat-value" style={{ color: data ? cpuColor(data.cpu_percent_used) : 'var(--text-dim)' }}>
              {data ? `${fmt(data.cpu_percent_used)}%` : 'no data yet'}
            </div>
            <div className="stat-label">CPU utilisation</div>
          </div>

          <div className="panel">
            <div className="panel-title">Last {vals.length} readings</div>
            {vals.length === 0 ? (
              <div className="muted" style={{ fontSize: 12.5 }}>No history yet</div>
            ) : (
              <>
                {/* Chart with value on hover */}
                <div style={{ position: 'relative', height: 56 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 40 }}>
                    {vals.map((v, i) => (
                      <div
                        key={i}
                        title={`${fmt(v)}%`}
                        style={{
                          flex: 1,
                          height: `${Math.max(4, Math.min(100, v))}%`,
                          background: cpuColor(v),
                          borderRadius: 1,
                          cursor: 'default',
                          opacity: i === vals.length - 1 ? 1 : 0.7,
                          transition: 'opacity 0.1s',
                        }}
                      />
                    ))}
                  </div>
                  {/* Min/Max/Avg labels */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                    <span style={{ fontSize: 10.5, fontFamily: 'var(--mono)', color: 'var(--text-faint)' }}>
                      min {fmt(minVal)}%
                    </span>
                    <span style={{ fontSize: 10.5, fontFamily: 'var(--mono)', color: 'var(--text-faint)' }}>
                      avg {fmt(avgVal)}%
                    </span>
                    <span style={{ fontSize: 10.5, fontFamily: 'var(--mono)', color: cpuColor(maxVal) }}>
                      peak {fmt(maxVal)}%
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── RAM ──────────────────────────────────────────────────────────────────────

function RamSection({ nodeId, ramTotalGb }) {
  const { data, loading, error, reload } = useFetch(() => getLatestRam(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader title="Memory usage" subtitle="collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="ram" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div> : !data ? (
        <div className="empty-state">No memory data yet.</div>
      ) : (
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="text-dim" style={{ fontSize: 13 }}>
              {fmt(data.ram_used_gb)} GB used of {ramTotalGb ?? '?'} GB
            </span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: data.ram_percent_used > 85 ? 'var(--red)' : data.ram_percent_used > 60 ? 'var(--amber)' : 'var(--green)' }}>
              {fmt(data.ram_percent_used)}%
            </span>
          </div>
          <div style={{ background: 'var(--bg)', borderRadius: 4, height: 8, overflow: 'hidden', border: '1px solid var(--border-bright)' }}>
            <div style={{ width: `${Math.min(100, data.ram_percent_used || 0)}%`, height: '100%', background: data.ram_percent_used > 85 ? 'var(--red)' : data.ram_percent_used > 60 ? 'var(--amber)' : 'var(--green)' }} />
          </div>
          <div className="text-dim" style={{ fontSize: 12, marginTop: 8 }}>{fmt(data.ram_available_gb)} GB available</div>
        </div>
      )}
    </div>
  );
}

// ─── Disk ─────────────────────────────────────────────────────────────────────

function DiskSection({ nodeId, diskTotalGb }) {
  const { data, loading, error, reload } = useFetch(() => getLatestDisk(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader title="Disk usage" subtitle="collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="disk" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div> : !data ? (
        <div className="empty-state">No disk data yet.</div>
      ) : (
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="text-dim" style={{ fontSize: 13 }}>
              {fmt(data.disk_used_gb)} GB used of {diskTotalGb ?? '?'} GB
            </span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: data.disk_percent_used > 90 ? 'var(--red)' : data.disk_percent_used > 75 ? 'var(--amber)' : 'var(--green)' }}>
              {fmt(data.disk_percent_used)}%
            </span>
          </div>
          <div style={{ background: 'var(--bg)', borderRadius: 4, height: 8, overflow: 'hidden', border: '1px solid var(--border-bright)' }}>
            <div style={{ width: `${Math.min(100, data.disk_percent_used || 0)}%`, height: '100%', background: data.disk_percent_used > 90 ? 'var(--red)' : data.disk_percent_used > 75 ? 'var(--amber)' : 'var(--green)' }} />
          </div>
          <div className="text-dim" style={{ fontSize: 12, marginTop: 8 }}>{fmt(data.disk_free_gb)} GB free</div>
        </div>
      )}
    </div>
  );
}

// ─── Network I/O ──────────────────────────────────────────────────────────────

function NetworkIoSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getLatestNetworkIo(nodeId), [nodeId]);
  function formatMb(mb) {
    if (mb == null) return '—';
    return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`;
  }
  return (
    <div className="section">
      <SectionHeader title="Network traffic" subtitle="cumulative since boot, collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="network_io" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div> : !data ? (
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

// ─── Processes ────────────────────────────────────────────────────────────────

const SORT_OPTIONS = [
  { key: 'received_at', label: 'Latest first' },
  { key: 'cpu_percent', label: 'CPU %' },
  { key: 'memory_percent', label: 'Memory %' },
  { key: 'name', label: 'Name A→Z' },
  { key: 'username', label: 'User' },
];

function ProcessesSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getProcessHistory(nodeId, 200), [nodeId]);
  const [sort, setSort] = useState('received_at');
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);

  const sorted = data ? [...data]
    .filter(p => !filter || (p.name || '').toLowerCase().includes(filter.toLowerCase()) || (p.username || '').toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      if (sort === 'received_at') return new Date(b.received_at) - new Date(a.received_at);
      if (sort === 'name') return (a.name || '').localeCompare(b.name || '');
      if (sort === 'username') return (a.username || '').localeCompare(b.username || '');
      return (b[sort] || 0) - (a[sort] || 0);
    }) : [];

  // Reset to first page whenever the filter/sort changes
  useEffect(() => { setPage(1); }, [filter, sort, data]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const paged = sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <div className="section">
      <SectionHeader
        title="Process activity"
        subtitle="new processes seen since last check, collected every minute"
        nodeId={nodeId} collector="processes" onResult={reload}
        extra={
          <input
            placeholder="filter by name / user…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', fontSize: 12, color: 'var(--text)', width: 180 }}
          />
        }
      />
      {error && <div className="error-banner">{error}</div>}

      {/* Sort pills */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <span className="text-dim" style={{ fontSize: 11.5, alignSelf: 'center', marginRight: 2 }}>Sort:</span>
        {SORT_OPTIONS.map(o => (
          <button key={o.key} onClick={() => setSort(o.key)} style={{
            padding: '2px 10px', borderRadius: 4, fontSize: 11.5,
            border: `1px solid ${sort === o.key ? 'var(--green)' : 'var(--border)'}`,
            background: sort === o.key ? 'rgba(95,217,122,0.08)' : 'transparent',
            color: sort === o.key ? 'var(--green)' : 'var(--text-dim)',
            cursor: 'pointer', fontFamily: 'var(--sans)',
          }}>
            {o.label}
          </button>
        ))}
        {data && (
          <span className="text-dim" style={{ fontSize: 11.5, alignSelf: 'center', marginLeft: 'auto' }}>
            {sorted.length} / {data.length} processes
          </span>
        )}
      </div>

      <div className="table-wrap">
        {loading ? <div className="loading-text">Loading…</div>
          : !data || data.length === 0 ? <div className="empty-state">No process data yet.</div>
          : sorted.length === 0 ? <div className="empty-state">No processes match "{filter}".</div>
          : (
            <table>
              <thead>
                <tr>
                  <th>Process</th>
                  <th>User</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Status</th>
                  <th>Seen</th>
                </tr>
              </thead>
              <tbody>
                {paged.map((p, i) => (
                  <tr key={i}>
                    <td>
                      <span className="mono">{p.name || '—'}</span>
                      <span className="text-dim" style={{ fontSize: 11, marginLeft: 5 }}>({p.pid})</span>
                      {p.cmdline && (
                        <div className="text-dim mono" style={{ fontSize: 10.5, marginTop: 2, maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.cmdline}>
                          {p.cmdline}
                        </div>
                      )}
                    </td>
                    <td className="text-dim">{p.username || '—'}</td>
                    <td style={{ color: (p.cpu_percent || 0) > 20 ? 'var(--amber)' : 'inherit', fontFamily: 'var(--mono)', fontSize: 12.5 }}>
                      {fmt(p.cpu_percent)}%
                    </td>
                    <td className="mono" style={{ fontSize: 12.5 }}>{fmt(p.memory_percent)}%</td>
                    <td>
                      <span className="badge" style={{ fontSize: 10 }}>{p.status || '—'}</span>
                    </td>
                    <td className="text-dim">{relativeTime(p.received_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
      {!loading && sorted.length > 0 && (
        <Pagination page={safePage} setPage={setPage} total={sorted.length} />
      )}
    </div>
  );
}

// ─── Active connections ───────────────────────────────────────────────────────

function ConnectionsSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getActiveConnections(nodeId), [nodeId]);
  const [page, setPage] = useState(1);

  const connections = data ? data.connections : [];

  useEffect(() => { setPage(1); }, [data]);

  const pageCount = Math.max(1, Math.ceil(connections.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const paged = connections.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <div className="section">
      <SectionHeader title="Active network connections" subtitle="snapshot, collected every 5 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="active_connections" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      <div className="table-wrap">
        {loading ? <div className="loading-text">Loading…</div>
          : connections.length === 0 ? <div className="empty-state">No active connections captured yet.</div>
          : (
            <table>
              <thead>
                <tr><th>Local</th><th>Remote</th><th>Status</th><th>Process</th></tr>
              </thead>
              <tbody>
                {paged.map((c, i) => (
                  <tr key={i}>
                    <td className="mono" style={{ fontSize: 12 }}>{c.local_ip}:{c.local_port}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{c.remote_ip ? `${c.remote_ip}:${c.remote_port}` : <span className="text-faint">listening</span>}</td>
                    <td><span className="badge">{c.status}</span></td>
                    <td className="text-dim">{c.process_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
      {!loading && connections.length > 0 && (
        <Pagination page={safePage} setPage={setPage} total={connections.length} />
      )}
    </div>
  );
}

// ─── Browser history ──────────────────────────────────────────────────────────

function BrowserHistorySection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getBrowserHistory(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader title="Browsing activity" subtitle="collected every 10 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="browser_history" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div>
        : !data ? <div className="empty-state">No browser history collected yet.</div>
        : (
          <div className="grid grid-2">
            {/* Most visited */}
            <div>
              <div className="panel-title" style={{ marginBottom: 8 }}>Most visited domains</div>
              <div className="table-wrap">
                {data.most_visited.length === 0 ? <div className="empty-state">None</div> : (
                  <table>
                    <thead><tr><th>Domain</th><th>Visits</th><th>Browsers</th></tr></thead>
                    <tbody>
                      {data.most_visited.slice(0, 12).map((d, i) => (
                        <tr key={i}>
                          <td>
                            <div className="mono" style={{ fontSize: 12.5 }}>{d.domain}</div>
                            {d.title && d.title !== d.domain && (
                              <div className="text-dim" style={{ fontSize: 11, marginTop: 2 }}>{d.title}</div>
                            )}
                          </td>
                          <td style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--green)' }}>{d.visit_count}</td>
                          <td className="text-dim" style={{ fontSize: 11 }}>
                            {Array.isArray(d.browsers) ? d.browsers.join(', ') : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Recently visited */}
            <div>
              <div className="panel-title" style={{ marginBottom: 8 }}>Recently visited</div>
              <div className="table-wrap">
                {data.recently_visited.length === 0 ? <div className="empty-state">None</div> : (
                  <table>
                    <thead><tr><th>Page</th><th>When</th></tr></thead>
                    <tbody>
                      {data.recently_visited.slice(0, 12).map((d, i) => (
                        <tr key={i}>
                          <td>
                            {/* Title if available, else URL, else domain */}
                            {d.title ? (
                              <>
                                <div style={{ fontSize: 12.5 }}>{d.title}</div>
                                <div className="mono text-dim" style={{ fontSize: 10.5, marginTop: 2 }}>
                                  {d.url || d.domain}
                                </div>
                              </>
                            ) : d.url ? (
                              <>
                                <div className="mono" style={{ fontSize: 12 }}>{d.domain}</div>
                                <div className="text-dim" style={{ fontSize: 10.5, marginTop: 2, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={d.url}>
                                  {d.url}
                                </div>
                              </>
                            ) : (
                              <span className="mono" style={{ fontSize: 12.5 }}>{d.domain}</span>
                            )}
                            {d.browser && (
                              <span className="badge" style={{ fontSize: 9.5, marginTop: 3 }}>{d.browser}</span>
                            )}
                          </td>
                          <td className="text-dim" style={{ whiteSpace: 'nowrap' }}>{timeAgo(d.last_visit_time)}</td>
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

// ─── Network config ───────────────────────────────────────────────────────────

function NetworkConfigSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getNetworkConfig(nodeId), [nodeId]);

  return (
    <div className="section">
      <SectionHeader title="Network configuration" subtitle="interfaces, DNS, routing — collected every 30 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="network_interfaces" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div>
        : !data ? <div className="empty-state">No network configuration collected yet.</div>
        : (
          <div className="grid grid-2">
            <div className="panel">
              <div className="panel-title">Interfaces</div>
              {data.interfaces.length === 0 ? (
                <div className="text-dim" style={{ fontSize: 12.5 }}>No interfaces collected yet — try refreshing</div>
              ) : data.interfaces.map((iface, i) => (
                <div key={i} style={{ marginBottom: 10, fontSize: 12.5 }}>
                  <div className="mono" style={{ fontWeight: 600 }}>{iface.interface_name}</div>
                  <div className="text-dim">{iface.ipv4 || 'no IPv4'}{iface.ipv6 ? ` · ${iface.ipv6}` : ''}</div>
                  {iface.mac_address && <div className="text-dim mono" style={{ fontSize: 11 }}>{iface.mac_address}</div>}
                </div>
              ))}
            </div>

            <div>
              <div className="panel" style={{ marginBottom: 10 }}>
                <div className="panel-title">DNS servers</div>
                {data.dns_servers.length === 0 ? (
                  <div className="text-dim" style={{ fontSize: 12.5 }}>
                    No DNS servers collected yet — click Refresh Now to pull live data
                  </div>
                ) : data.dns_servers.map((addr, i) => (
                  <div key={i} className="mono" style={{ fontSize: 13, marginBottom: 4 }}>{addr}</div>
                ))}
              </div>

              <div className="panel">
                <div className="panel-title">Routing table</div>
                {data.routing_table.length === 0 ? (
                  <div className="text-dim" style={{ fontSize: 12.5 }}>No routing data yet</div>
                ) : (
                  <div style={{ maxHeight: 160, overflowY: 'auto' }}>
                    {data.routing_table.map((route, i) => (
                      <div key={i} className="mono text-dim" style={{ fontSize: 11.5, marginBottom: 3, lineHeight: 1.5 }}>
                        {route}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
    </div>
  );
}

// ─── Security ─────────────────────────────────────────────────────────────────

function SecuritySection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getSecurityStatus(nodeId), [nodeId]);

  const checks = data ? [
    { label: 'Firewall', ok: data.firewall_active, good: 'Active', bad: 'Inactive', detail: data.firewall_tool },
    { label: 'Disk encryption', ok: data.disk_encrypted, good: 'Encrypted', bad: 'Not encrypted' },
    { label: 'Root SSH login', ok: !data.root_login_permitted, good: 'Blocked', bad: 'Permitted ⚠' },
    { label: 'Password SSH auth', ok: !data.password_auth_permitted, good: 'Disabled', bad: 'Enabled ⚠' },
    { label: 'Access control', ok: data.mac_enabled, good: 'Enforcing', bad: 'Not enforcing', detail: data.mac_tool },
  ] : [];

  return (
    <div className="section">
      <SectionHeader title="Security posture" subtitle="collected every 30 minutes"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="security_status" onResult={reload} />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div>
        : !data ? <div className="empty-state">No security data collected yet.</div>
        : (
          <div className="grid grid-3">
            {checks.map((c) => (
              <div className="panel" key={c.label}>
                <div className="panel-title">{c.label}</div>
                <div className="stat-value" style={{ fontSize: 18, color: c.ok === null ? 'var(--text-dim)' : c.ok ? 'var(--green)' : 'var(--red)' }}>
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

// ─── Logs ─────────────────────────────────────────────────────────────────────

function LogsSection({ nodeId }) {
  const { data: sysLogs, loading: l1, reload: r1 } = useFetch(() => getSystemLogs(nodeId), [nodeId]);
  const { data: authLogs, loading: l2, reload: r2 } = useFetch(() => getAuthEvents(nodeId), [nodeId]);

  return (
    <div className="section">
      <div className="section-title">
        <span>System &amp; auth activity <span className="text-dim" style={{ fontWeight: 400, fontSize: 12, marginLeft: 8 }}>collected every 5 minutes</span></span>
        <span style={{ display: 'flex', gap: 8 }}>
          <RefreshButton nodeId={nodeId} collector="system_logs" onResult={r1} />
          <RefreshButton nodeId={nodeId} collector="auth_events" onResult={r2} />
        </span>
      </div>
      <div className="grid grid-2">
        <div>
          <div className="panel-title" style={{ marginBottom: 8 }}>System log (recent)</div>
          <div className="table-wrap" style={{ maxHeight: 220, overflowY: 'auto' }}>
            {l1 ? <div className="loading-text">Loading…</div>
              : !sysLogs || sysLogs.log_lines.length === 0 ? <div className="empty-state">No recent system log lines.</div>
              : <div className="json-cell" style={{ padding: 12 }}>{sysLogs.log_lines.slice(0, 20).join('\n')}</div>}
          </div>
        </div>
        <div>
          <div className="panel-title" style={{ marginBottom: 8 }}>Authentication events</div>
          <div className="table-wrap" style={{ maxHeight: 220, overflowY: 'auto' }}>
            {l2 ? <div className="loading-text">Loading…</div>
              : !authLogs || authLogs.log_lines.length === 0 ? <div className="empty-state">No recent auth events.</div>
              : <div className="json-cell" style={{ padding: 12 }}>{authLogs.log_lines.slice(0, 20).join('\n')}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Installed packages ───────────────────────────────────────────────────────

function PackagesSection({ nodeId }) {
  const { data, loading, error, reload } = useFetch(() => getInstalledPackages(nodeId), [nodeId]);
  const [pkgFilter, setPkgFilter] = useState('');

  const filtered = data ? data.packages.filter(p => !pkgFilter || p.toLowerCase().includes(pkgFilter.toLowerCase())) : [];

  return (
    <div className="section">
      <SectionHeader title="Installed packages" subtitle="collected once daily"
        lastUpdated={data && relativeTime(data.received_at)} nodeId={nodeId} collector="installed_packages" onResult={reload}
        extra={data && (
          <input placeholder="search packages…" value={pkgFilter} onChange={e => setPkgFilter(e.target.value)}
            style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', fontSize: 12, color: 'var(--text)', width: 160 }} />
        )}
      />
      {error && <div className="error-banner">{error}</div>}
      {loading ? <div className="loading-text">Loading…</div>
        : !data ? <div className="empty-state">No package list collected yet.</div>
        : (
          <div className="panel">
            <div className="text-dim" style={{ fontSize: 12.5, marginBottom: 8 }}>
              {filtered.length}{pkgFilter ? ` match "${pkgFilter}" of ` : ' '}
              {data.packages.length} packages installed
            </div>
            <div className="mono text-dim" style={{ fontSize: 11.5, maxHeight: 120, overflowY: 'auto', lineHeight: 1.8 }}>
              {filtered.slice(0, 100).join(', ')}{filtered.length > 100 ? `… +${filtered.length - 100} more` : ''}
            </div>
          </div>
        )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TelemetryPage() {
  const { nodeId } = useParams();
  const { data: hardwareInfo } = useFetch(() => getHardwareInfo(nodeId), [nodeId]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Telemetry</div>
          <div className="page-sub">Live data from the agent — hover charts for values, click Refresh Now on any section to pull fresh data immediately.</div>
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