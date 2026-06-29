import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import {
  getFirewallRules,
  getFirewallStatus,
  createFirewallRule,
  updateFirewallRule,
  deleteFirewallRule,
} from '../api/client';
import FirewallRuleForm from '../components/FirewallRuleForm';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

function paramsSummary(rule) {
  const p = rule.params || {};
  switch (rule.rule_type) {
    case 'port': return `port ${p.port}/${p.protocol} (${p.direction})`;
    case 'ip': return `${p.ip} (${p.direction})`;
    case 'ip_port': return `${p.ip}:${p.port}/${p.protocol} (${p.direction})`;
    case 'domain': return p.domain;
    case 'bandwidth': return `${p.rate_mbit} Mbps on ${p.interface}`;
    case 'user_port': return `${p.username} → port ${p.port}/${p.protocol}`;
    default: return JSON.stringify(p);
  }
}

export default function FirewallPage() {
  const { nodeId } = useParams();
  const showToast = useToast();
  const { data: rules, loading, error, reload } = useFetch(() => getFirewallRules(nodeId), [nodeId]);
  const { data: status, reload: reloadStatus } = useFetch(() => getFirewallStatus(nodeId), [nodeId]);

  const [formOpen, setFormOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [deletingRule, setDeletingRule] = useState(null);

  async function handleSave(payload) {
    try {
      if (editingRule) {
        await updateFirewallRule(nodeId, editingRule.id, payload);
        showToast(`Rule #${editingRule.id} updated`);
      } else {
        await createFirewallRule(nodeId, payload);
        showToast('Firewall rule created');
      }
      setFormOpen(false);
      setEditingRule(null);
      reload();
      reloadStatus();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  async function handleDelete() {
    try {
      await deleteFirewallRule(nodeId, deletingRule.id);
      showToast(`Rule #${deletingRule.id} deleted`);
      setDeletingRule(null);
      reload();
      reloadStatus();
    } catch (err) {
      showToast(err.message, 'error');
      setDeletingRule(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Firewall Rules</div>
          <div className="page-sub">Create, edit and enforce rules on this node</div>
        </div>
        <button className="btn btn-primary" onClick={() => { setEditingRule(null); setFormOpen(true); }}>
          + New rule
        </button>
      </div>

      {status && (
        <div className="grid grid-4 section">
          <div className="panel">
            <div className="panel-title">Total rules</div>
            <div className="stat-value">{status.total_rules}</div>
          </div>
          <div className="panel">
            <div className="panel-title">Enabled</div>
            <div className="stat-value green">{status.enabled_rules}</div>
          </div>
          <div className="panel">
            <div className="panel-title">Applied</div>
            <div className="stat-value green">{status.applied_rules}</div>
          </div>
          <div className="panel">
            <div className="panel-title">Pending</div>
            <div className="stat-value amber">{status.pending_rules}</div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading rules…</div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Action</th>
                <th>Params</th>
                <th>Schedule</th>
                <th>Enabled</th>
                <th>Applied</th>
                <th>Description</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules?.length === 0 && (
                <tr className="empty-row"><td colSpan={9}>No firewall rules yet. Create one to get started.</td></tr>
              )}
              {rules?.map((rule) => (
                <tr key={rule.id}>
                  <td className="mono text-dim">#{rule.id}</td>
                  <td><span className="badge">{rule.rule_type}</span></td>
                  <td><span className={`badge ${rule.action}`}>{rule.action}</span></td>
                  <td className="mono">{paramsSummary(rule)}</td>
                  <td className="text-dim">
                    {rule.schedule ? `${rule.schedule.start_time}–${rule.schedule.end_time}` : '—'}
                  </td>
                  <td><span className={`badge ${rule.enabled ? 'allow' : 'disabled'}`}>{rule.enabled ? 'yes' : 'no'}</span></td>
                  <td><span className={`badge ${rule.applied ? 'applied' : 'pending'}`}>{rule.applied ? 'applied' : 'pending'}</span></td>
                  <td className="text-dim">{rule.description || '—'}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-ghost btn-sm" onClick={() => { setEditingRule(rule); setFormOpen(true); }}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => setDeletingRule(rule)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {formOpen && (
        <FirewallRuleForm
          initial={editingRule}
          onSave={handleSave}
          onCancel={() => { setFormOpen(false); setEditingRule(null); }}
        />
      )}

      {deletingRule && (
        <ConfirmDialog
          title="Delete firewall rule?"
          message={`This will delete rule #${deletingRule.id} (${paramsSummary(deletingRule)}). If it's currently applied, a delete command will be queued for the node.`}
          onConfirm={handleDelete}
          onCancel={() => setDeletingRule(null)}
        />
      )}
    </div>
  );
}
