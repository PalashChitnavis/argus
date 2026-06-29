import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import NodesPage from './pages/NodesPage';
import DashboardPage from './pages/DashboardPage';
import TelemetryPage from './pages/TelemetryPage';
import FirewallPage from './pages/FirewallPage';
import CommandsPage from './pages/CommandsPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<NodesPage />} />
        <Route path="nodes" element={<NodesPage />} />
        <Route path="nodes/:nodeId/dashboard" element={<DashboardPage />} />
        <Route path="nodes/:nodeId/telemetry" element={<TelemetryPage />} />
        <Route path="nodes/:nodeId/firewall" element={<FirewallPage />} />
        <Route path="nodes/:nodeId/commands" element={<CommandsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
