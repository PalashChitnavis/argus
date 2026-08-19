import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import {
  getFirewallRules,
  getFirewallStatus,
  createFirewallRule,
  updateFirewallRule,
  deleteFirewallRule,
  getFirewallHistory,
  getCommand,
} from '../api/client';
import FirewallRuleForm from '../components/FirewallRuleForm';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';
import { describeRule, ruleTypeLabel, paramsSummary } from '../lib/firewallText';

// ─── tiny helpers ────────────────────────────────────────────────────────────

function fmt(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function describeHistoryRule(entry) {
  return describeRule({ rule_type: entry.rule_type, action: entry.action, params: entry.params });
}

// Poll a command until executed (max ~30 s) then call onDone(success, message)
function usePendingCommand(commandId, onDone) {
  const timerRef = useRef(null);
  const nodeId = useRef(null);
  const { nodeId: nid } = useParams ? { nodeId: undefined } : {};

  useEffect(() => {
    if (!commandId) return;
    // commandId is enough — we fetch it from the node in the parent
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [commandId]);
}

// ─── Badge components ─────────────────────────────────────────────────────────

function StatusBadge({ rule }) {
  if (!rule.enabled) return <span className="badge disabled">paused</span>;
  if (rule.applied) return <span className="badge applied">live on node</span>;
  return <span className="badge pending">waiting to apply</span>;
}

function EventBadge({ event, success }) {
  if (!success) return <span className="badge" style={{ color: 'var(--red)', borderColor: 'var(--red-dim)' }}>failed</span>;
  if (event === 'applied') return <span className="badge applied">applied</span>;
  if (event === 'deleted') return <span className="badge" style={{ color: 'var(--text-dim)', borderColor: 'var(--border-bright)' }}>deleted</span>;
  return <span className="badge">{event}</span>;
}

// ─── Active rules tab ─────────────────────────────────────────────────────────

function ActiveRulesTab({ nodeId, onHistoryNeeded }) {
  const showToast = useToast();
  const { data: rules, loading, error, reload } = useFetch(() => getFirewallRules(nodeId), [nodeId]);
  const { data: status, reload: reloadStatus } = useFetch(() => getFirewallStatus(nodeId), [nodeId]);

  const [formOpen, setFormOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [deletingRule, setDeletingRule] = useState(null);

  // Per-rule command tracking: { [ruleId]: { commandId, polling, label } }
  const [ruleStatus, setRuleStatus] = useState({});

  function startPolling(ruleId, commandId, label, nodeId) {
    setRuleStatus(s => ({ ...s, [ruleId]: { commandId, polling: true, label } }));

    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const cmd = await getCommand(nodeId, commandId);
        if (cmd.executed) {
          clearInterval(interval);
          const success = cmd.result?.success !== false;
          const msg = cmd.result?.data?.output || (success ? `${label} confirmed by node` : `${label} failed on node`);
          showToast(msg, success ? 'success' : 'error');
          setRuleStatus(s => {
            const next = { ...s };
            delete next[ruleId];
            return next;
          });
          reload();
          reloadStatus();
        }
      } catch {
        // ignore fetch errors during polling
      }
      if (attempts > 18) { // ~3 minutes
        clearInterval(interval);
        setRuleStatus(s => {
          const next = { ...s };
          delete next[ruleId];
          return next;
        });
      }
    }, 5000);
  }

  async function handleSave(payload) {
    try {
      let saved;
      if (editingRule) {
        saved = await updateFirewallRule(nodeId, editingRule.id, payload);
        showToast('Rule updated — waiting for node to apply…');
      } else {
        saved = await createFirewallRule(nodeId, payload);
        showToast('Rule created — waiting for node to apply…');
      }
      setFormOpen(false);
      setEditingRule(null);
      reload();
      reloadStatus();

      // Start polling for the command result
      // We need to find the most recent unexecuted command; simplest heuristic:
      // Re-fetch rules, find this rule, then poll status by watching its applied flag
      if (saved?.id) {
        // Poll rule applied status directly (simpler than command polling)
        pollRuleApplied(saved.id, payload.enabled ? 'Rule applied' : 'Rule updated');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function pollRuleApplied(ruleId, successLabel) {
    setRuleStatus(s => ({ ...s, [ruleId]: { polling: true, label: 'Applying…' } }));
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const allRules = await getFirewallRules(nodeId);
        const rule = allRules.find(r => r.id === ruleId);
        if (!rule) {
          // Rule was deleted
          clearInterval(interval);
          setRuleStatus(s => { const n = { ...s }; delete n[ruleId]; return n; });
          return;
        }
        if (rule.applied) {
          clearInterval(interval);
          showToast(successLabel + ' — confirmed live on node ✓', 'success');
          setRuleStatus(s => { const n = { ...s }; delete n[ruleId]; return n; });
          reload();
          reloadStatus();
        }
      } catch { /* ignore */ }
      if (attempts > 24) { // 2 min
        clearInterval(interval);
        setRuleStatus(s => { const n = { ...s }; delete n[ruleId]; return n; });
        showToast('Node did not confirm within 2 min — check node connectivity', 'error');
      }
    }, 5000);
  }

  async function handleDelete() {
    const rule = deletingRule;
    try {
      await deleteFirewallRule(nodeId, rule.id);
      setDeletingRule(null);
      showToast(`Delete command sent — node will remove the rule shortly`);
      reload();
      reloadStatus();
      // No polling needed for delete — node will call apply-status on its own
      // but we can show a transient indicator
      if (rule.enabled) {
        setTimeout(() => { reload(); reloadStatus(); }, 12000);
      }
    } catch (err) {
      showToast(err.message, 'error');
      setDeletingRule(null);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div />
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => { reload(); reloadStatus(); }} title="Refresh">
            ↻ Refresh
          </button>
          <button className="btn btn-primary" onClick={() => { setEditingRule(null); setFormOpen(true); }}>
            + New rule
          </button>
        </div>
      </div>

      {status && (
        <div className="grid grid-4 section">
          <div className="panel">
            <div className="panel-title">Total rules</div>
            <div className="stat-value">{status.total_rules}</div>
            <div className="stat-label">rules created</div>
          </div>
          <div className="panel">
            <div className="panel-title">Enabled</div>
            <div className="stat-value green">{status.enabled_rules}</div>
            <div className="stat-label">active, not paused</div>
          </div>
          <div className="panel">
            <div className="panel-title">Live on node</div>
            <div className="stat-value green">{status.applied_rules}</div>
            <div className="stat-label">confirmed by agent</div>
          </div>
          <div className="panel">
            <div className="panel-title">Pending</div>
            <div className="stat-value amber">{status.pending_rules}</div>
            <div className="stat-label">awaiting node check-in</div>
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

          {rules?.map((rule) => {
            const rs = ruleStatus[rule.id];
            return (
              <div className="panel firewall-rule-card" key={rule.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    {/* Badge row */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
                      <span className={`badge ${rule.action}`}>{ruleTypeLabel(rule.rule_type)}</span>
                      <StatusBadge rule={rule} />
                      {rs?.polling && (
                        <span className="badge pending" style={{ animation: 'pulse 1.5s infinite' }}>
                          ⟳ {rs.label || 'Applying…'}
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>
                      {describeRule(rule)}
                    </div>

                    {/* Params */}
                    <div className="text-dim mono" style={{ fontSize: 11.5, marginBottom: rule.description || rule.schedule ? 4 : 0 }}>
                      {paramsSummary(rule)}
                    </div>

                    {/* Schedule */}
                    {rule.schedule && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>⏱</span>
                        <span className="text-dim" style={{ fontSize: 12 }}>
                          Active {rule.schedule.start_time} – {rule.schedule.end_time}
                        </span>
                      </div>
                    )}

                    {/* User description */}
                    {rule.description && (
                      <div className="text-dim" style={{ fontSize: 12, marginTop: 4, fontStyle: 'italic' }}>
                        "{rule.description}"
                      </div>
                    )}

                    {/* Created at */}
                    <div className="text-dim" style={{ fontSize: 11, marginTop: 6, color: 'var(--text-faint)' }}>
                      Created {fmt(rule.created_at)}
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => { setEditingRule(rule); setFormOpen(true); }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => setDeletingRule(rule)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
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
          message={`"${describeRule(deletingRule)}" will be removed. If it's live on the node, a command will be sent to undo it.`}
          onConfirm={handleDelete}
          onCancel={() => setDeletingRule(null)}
        />
      )}
    </div>
  );
}

// ─── History tab ──────────────────────────────────────────────────────────────

function HistoryTab({ nodeId }) {
  const { data: history, loading, error, reload } = useFetch(() => getFirewallHistory(nodeId, 200), [nodeId]);
  const showToast = useToast();
  const [reapplying, setReapplying] = useState(null);

  async function handleReapply(entry) {
    setReapplying(entry.id);
    try {
      await createFirewallRule(nodeId, {
        rule_type: entry.rule_type,
        action: entry.action,
        params: entry.params,
        schedule: entry.schedule || null,
        description: entry.description || null,
        enabled: true,
      });
      showToast(`Rule queued — "${describeHistoryRule(entry)}" will apply on next check-in`);
      reload();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setReapplying(null);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <button className="btn btn-ghost btn-sm" onClick={reload}>↻ Refresh</button>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading history…</div>}

      {!loading && !error && history?.length === 0 && (
        <div className="table-wrap">
          <div className="empty-state">No history yet. Apply or delete rules to see activity here.</div>
        </div>
      )}

      {!loading && !error && history?.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Event</th>
                <th>Rule</th>
                <th>Type</th>
                <th>Schedule</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.id}>
                  <td className="mono" style={{ fontSize: 11.5, whiteSpace: 'nowrap', color: 'var(--text-dim)' }}>
                    {fmt(entry.created_at)}
                  </td>
                  <td>
                    <EventBadge event={entry.event} success={entry.success} />
                  </td>
                  <td style={{ fontSize: 13 }}>{describeHistoryRule(entry)}</td>
                  <td>
                    <span className="badge" style={{ fontSize: 10.5 }}>{ruleTypeLabel(entry.rule_type)}</span>
                  </td>
                  <td className="text-dim" style={{ fontSize: 12 }}>
                    {entry.schedule ? `${entry.schedule.start_time}–${entry.schedule.end_time}` : '—'}
                  </td>
                  <td className="text-dim mono" style={{ fontSize: 11, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.message || '—'}
                  </td>
                  <td>
                    {entry.event !== 'deleted' && (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => handleReapply(entry)}
                        disabled={reapplying === entry.id}
                        title="Create a new rule from this history entry"
                      >
                        {reapplying === entry.id ? '…' : '↺ Reapply'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Page shell ───────────────────────────────────────────────────────────────

export default function FirewallPage() {
  const { nodeId } = useParams();
  const [tab, setTab] = useState('rules');

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Firewall</div>
          <div className="page-sub">
            Rules created here are queued for the node and applied automatically on the next poll (usually within 10 s).
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 20, borderBottom: '1px solid var(--border)' }}>
        {[['rules', 'Active Rules'], ['history', 'History']].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              background: 'none',
              border: 'none',
              padding: '8px 16px',
              fontSize: 13,
              fontWeight: 500,
              color: tab === key ? 'var(--green)' : 'var(--text-dim)',
              borderBottom: `2px solid ${tab === key ? 'var(--green)' : 'transparent'}`,
              cursor: 'pointer',
              marginBottom: -1,
              transition: 'color 0.15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'rules' && <ActiveRulesTab nodeId={nodeId} />}
      {tab === 'history' && <HistoryTab nodeId={nodeId} />}
    </div>
  );
}
