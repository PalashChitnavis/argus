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
import { describeRule, ruleTypeLabel, paramsSummary } from '../lib/firewallText';

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
        showToast(`Rule updated`);
      } else {
        await createFirewallRule(nodeId, payload);
        showToast('Firewall rule created — it will apply next time the node checks in');
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
      showToast(`Rule deleted`);
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
          <div className="page-title">Firewall</div>
          <div className="page-sub">
            Rules you create here are queued for the node and applied the next time it checks in (usually within seconds).
          </div>
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
            <div className="stat-label">rules you've created</div>
          </div>
          <div className="panel">
            <div className="panel-title">Enabled</div>
            <div className="stat-value green">{status.enabled_rules}</div>
            <div className="stat-label">turned on, not paused</div>
          </div>
          <div className="panel">
            <div className="panel-title">Applied</div>
            <div className="stat-value green">{status.applied_rules}</div>
            <div className="stat-label">confirmed live on the node</div>
          </div>
          <div className="panel">
            <div className="panel-title">Pending</div>
            <div className="stat-value amber">{status.pending_rules}</div>
            <div className="stat-label">waiting for the node to apply</div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading rules…</div>}

      {!loading && !error && (
        <div className="section">
          {rules?.length === 0 && (
            <div className="table-wrap">
              <div className="empty-state">No firewall rules yet. Create one to start controlling this node's network access.</div>
            </div>
          )}

          {rules?.map((rule) => (
            <div className="panel" key={rule.id} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="badge">{ruleTypeLabel(rule.rule_type)}</span>
                    {!rule.enabled && <span className="badge disabled">paused</span>}
                    {rule.enabled && (
                      <span className={`badge ${rule.applied ? 'applied' : 'pending'}`}>
                        {rule.applied ? 'live on node' : 'waiting to apply'}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{describeRule(rule)}</div>
                  <div className="text-dim mono" style={{ fontSize: 11.5, marginTop: 3 }}>{paramsSummary(rule)}</div>
                  {rule.description && (
                    <div className="text-dim" style={{ fontSize: 12.5, marginTop: 4, fontStyle: 'italic' }}>"{rule.description}"</div>
                  )}
                  {rule.schedule && (
                    <div className="text-dim" style={{ fontSize: 12, marginTop: 4 }}>
                      Active only between {rule.schedule.start_time} and {rule.schedule.end_time}
                    </div>
                  )}
                </div>
                <div className="row-actions" style={{ flexShrink: 0 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => { setEditingRule(rule); setFormOpen(true); }}>Edit</button>
                  <button className="btn btn-danger btn-sm" onClick={() => setDeletingRule(rule)}>Delete</button>
                </div>
              </div>
            </div>
          ))}
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
          title="Delete this rule?"
          message={`This will remove "${describeRule(deletingRule)}". If it's currently live on the node, a command will be sent to undo it there too.`}
          onConfirm={handleDelete}
          onCancel={() => setDeletingRule(null)}
        />
      )}
    </div>
  );
}
