import { useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getNodes } from '../api/client';
import StatusPill from '../components/StatusPill';

function timeAgo(iso) {
  if (!iso) return 'never';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function NodesPage() {
  const navigate = useNavigate();
  const { data: nodes, loading, error, reload } = useFetch(getNodes, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Nodes</div>
          <div className="page-sub">All endpoints registered with this Argus backend</div>
        </div>
        <button className="btn" onClick={reload}>Refresh</button>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading nodes…</div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Hostname</th>
                <th>Machine ID</th>
                <th>Registered</th>
                <th>Last Seen</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {nodes?.length === 0 && (
                <tr className="empty-row"><td colSpan={6}>No nodes have registered yet.</td></tr>
              )}
              {nodes?.map((node) => (
                <tr key={node.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/nodes/${node.id}/overview`)}>
                  <td><StatusPill status={node.status} /></td>
                  <td className="mono">{node.hostname}</td>
                  <td className="mono text-dim">{node.machine_id}</td>
                  <td className="text-dim">{new Date(node.enrolled_at).toLocaleString()}</td>
                  <td className="text-dim">{timeAgo(node.last_seen)}</td>
                  <td className="text-dim">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
