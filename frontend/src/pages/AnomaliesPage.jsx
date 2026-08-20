import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { runAnomalyScan, getAnomalies, dismissAnomaly } from '../api/client';
import { useToast } from '../components/Toast';
import { featureLabel, featureDisplayValue, zScoreDirection } from '../lib/anomalyText';

function fmt(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function SeverityBadge({ score }) {
  // IsolationForest decision_function: more negative = more anomalous.
  const severe = score < -0.15;
  return (
    <span
      className="badge"
      style={
        severe
          ? { color: 'var(--red)', borderColor: 'var(--red-dim)', background: 'rgba(224,82,77,0.08)' }
          : { color: 'var(--amber)', borderColor: 'var(--amber-dim)', background: 'rgba(232,162,61,0.08)' }
      }
    >
      {severe ? 'high anomaly' : 'anomaly'}
    </span>
  );
}

function ContributingFeatureChip({ cf }) {
  const dir = zScoreDirection(cf.z_score);
  const color = dir === 'high' ? 'var(--red)' : dir === 'low' ? 'var(--blue)' : 'var(--text-dim)';
  const arrow = dir === 'high' ? '↑' : dir === 'low' ? '↓' : '→';
  return (
    <span
      className="mono"
      style={{
        fontSize: 11.5,
        color,
        border: '1px solid var(--border-bright)',
        borderRadius: 4,
        padding: '2px 6px',
        display: 'inline-flex',
        gap: 4,
        alignItems: 'center',
      }}
      title={`z-score ${cf.z_score}`}
    >
      {arrow} {featureLabel(cf.feature)}: {featureDisplayValue(cf.feature, cf.value)}
    </span>
  );
}

function AnomalyCard({ anomaly, onDismiss, dismissing }) {
  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
            <SeverityBadge score={anomaly.anomaly_score} />
            <span className="text-dim mono" style={{ fontSize: 11.5 }}>
              score {anomaly.anomaly_score.toFixed(3)}
            </span>
          </div>

          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Unusual activity window: {fmt(anomaly.window_start)} – {fmt(anomaly.window_end)}
          </div>

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {anomaly.contributing_features.map((cf) => (
              <ContributingFeatureChip key={cf.feature} cf={cf} />
            ))}
          </div>

          <div className="text-dim" style={{ fontSize: 11, marginTop: 8, color: 'var(--text-faint)' }}>
            Detected {fmt(anomaly.detected_at)}
          </div>
        </div>

        <button
          className="btn btn-ghost btn-sm"
          onClick={() => onDismiss(anomaly)}
          disabled={dismissing === anomaly.id}
        >
          {dismissing === anomaly.id ? '…' : 'Dismiss'}
        </button>
      </div>
    </div>
  );
}

export default function AnomaliesPage() {
  const { nodeId } = useParams();
  const showToast = useToast();
  const { data: anomalies, loading, error, reload } = useFetch(() => getAnomalies(nodeId), [nodeId]);
  const [scanning, setScanning] = useState(false);
  const [dismissing, setDismissing] = useState(null);
  const [lastScanMessage, setLastScanMessage] = useState(null);

  async function handleScan() {
    setScanning(true);
    setLastScanMessage(null);
    try {
      const result = await runAnomalyScan(nodeId, 6);
      if (result.message) {
        setLastScanMessage(result.message);
      } else if (result.anomalies_found === 0) {
        showToast(`Scanned ${result.windows_scanned} windows — nothing unusual found`);
      } else {
        showToast(`Scanned ${result.windows_scanned} windows — ${result.anomalies_found} flagged`, 'error');
      }
      reload();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setScanning(false);
    }
  }

  async function handleDismiss(anomaly) {
    setDismissing(anomaly.id);
    try {
      await dismissAnomaly(nodeId, anomaly.id);
      showToast('Anomaly dismissed');
      reload();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setDismissing(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Anomalies</div>
          <div className="page-sub">
            An IsolationForest model is fit fresh on this node's last 6 hours of telemetry (CPU, RAM, disk,
            network, processes, connections, browser activity, logs) each time you scan — flagging 5-minute
            windows that look statistically unlike the node's own recent behaviour.
          </div>
        </div>
        <button className="btn btn-primary" onClick={handleScan} disabled={scanning}>
          {scanning ? 'Scanning…' : '⟳ Scan now'}
        </button>
      </div>

      {lastScanMessage && (
        <div className="error-banner" style={{ borderColor: 'var(--amber-dim)', color: 'var(--amber)' }}>
          {lastScanMessage}
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading anomalies…</div>}

      {!loading && !error && anomalies?.length === 0 && (
        <div className="table-wrap">
          <div className="empty-state">
            No active anomalies. Click "Scan now" to check this node's recent telemetry.
          </div>
        </div>
      )}

      {!loading && !error && anomalies?.length > 0 && (
        <div className="section">
          {anomalies.map((a) => (
            <AnomalyCard key={a.id} anomaly={a} onDismiss={handleDismiss} dismissing={dismissing} />
          ))}
        </div>
      )}
    </div>
  );
}
