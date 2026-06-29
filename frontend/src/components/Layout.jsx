import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getNodes } from '../api/client';

const NAV_ITEMS = [
  { to: 'overview', label: 'Overview' },
  { to: 'telemetry', label: 'Telemetry' },
  { to: 'firewall', label: 'Firewall' },
];

export default function Layout() {
  const { nodeId } = useParams();
  const navigate = useNavigate();
  const { data: nodes, loading } = useFetch(getNodes, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <span className="brand-eye">◉</span> ARGUS
          </span>
        </div>

        <div className="node-picker">
          <div className="node-picker-label">Nodes</div>
          {loading && <div className="muted" style={{ padding: '6px 8px', fontSize: 12 }}>Loading…</div>}
          {!loading && nodes?.length === 0 && (
            <div className="muted" style={{ padding: '6px 8px', fontSize: 12 }}>No nodes registered</div>
          )}
          {nodes?.map((node) => (
            <div
              key={node.id}
              className={`node-item ${String(node.id) === nodeId ? 'active' : ''}`}
              onClick={() => navigate(`/nodes/${node.id}/overview`)}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: node.status === 'online' ? 'var(--green)' : 'var(--text-faint)',
                  flexShrink: 0,
                }}
              />
              {node.hostname}
            </div>
          ))}
        </div>

        {nodeId && (
          <nav className="nav">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={`/nodes/${nodeId}/${item.to}`}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="sidebar-footer">argus-backend · v1</div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
