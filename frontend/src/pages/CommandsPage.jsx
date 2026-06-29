import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import {
  getCommands,
  deleteCommand,
  createRefreshCommand,
  createEnforceCommand,
  createDeleteRuleCommand,
  createGetRulesCommand,
} from '../api/client';
import CommandForm from '../components/CommandForm';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

export default function CommandsPage() {
  const { nodeId } = useParams();
  const showToast = useToast();
  const { data: commands, loading, error, reload } = useFetch(() => getCommands(nodeId, 30), [nodeId]);

  const [formOpen, setFormOpen] = useState(false);
  const [deletingCmd, setDeletingCmd] = useState(null);
  const [expanded, setExpanded] = useState(null);

  async function handleCreate(type, payload) {
    try {
      if (type === 'refresh') await createRefreshCommand(nodeId, payload.collector);
      else if (type === 'enforce') await createEnforceCommand(nodeId, payload);
      else if (type === 'delete-rule') await createDeleteRuleCommand(nodeId, payload);
      else if (type === 'get-rules') await createGetRulesCommand(nodeId);
      showToast('Command queued');
      setFormOpen(false);
      reload();
    } catch (err) {
      showToast(err.message, 'error');
      throw err;
    }
  }

  async function handleDelete() {
    try {
      await deleteCommand(nodeId, deletingCmd.command_id);
      showToast('Command deleted');
      setDeletingCmd(null);
      reload();
    } catch (err) {
      showToast(err.message, 'error');
      setDeletingCmd(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Commands</div>
          <div className="page-sub">Queue and track commands sent to this node</div>
        </div>
        <button className="btn btn-primary" onClick={() => setFormOpen(true)}>+ New command</button>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="loading-text">Loading commands…</div>}

      {!loading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Command ID</th>
                <th>Type</th>
                <th>Created</th>
                <th>Status</th>
                <th>Result</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {commands?.length === 0 && (
                <tr className="empty-row"><td colSpan={6}>No commands queued yet.</td></tr>
              )}
              {commands?.map((cmd) => (
                <>
                  <tr key={cmd.command_id} style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === cmd.command_id ? null : cmd.command_id)}>
                    <td className="mono text-dim">{cmd.command_id.slice(0, 8)}…</td>
                    <td><span className="badge">{cmd.type}</span></td>
                    <td className="text-dim">{new Date(cmd.created_at).toLocaleString()}</td>
                    <td><span className={`badge ${cmd.executed ? 'executed' : 'queued'}`}>{cmd.executed ? 'executed' : 'queued'}</span></td>
                    <td>
                      {cmd.result ? (
                        <span className={`badge ${cmd.result.success ? 'allow' : 'deny'}`}>
                          {cmd.result.success ? 'success' : 'failed'}
                        </span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td>
                      {!cmd.executed && (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={(e) => { e.stopPropagation(); setDeletingCmd(cmd); }}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded === cmd.command_id && (
                    <tr>
                      <td colSpan={6} style={{ background: 'var(--bg-hover)' }}>
                        <div className="json-cell">
                          <strong style={{ color: 'var(--text-dim)' }}>payload:</strong> {JSON.stringify(cmd.payload, null, 2)}
                          {cmd.result?.data && (
                            <>
                              {'\n\n'}<strong style={{ color: 'var(--text-dim)' }}>result data:</strong> {JSON.stringify(cmd.result.data, null, 2)}
                            </>
                          )}
                          {cmd.result?.error_message && (
                            <>
                              {'\n\n'}<strong style={{ color: 'var(--red)' }}>error:</strong> {cmd.result.error_message}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {formOpen && <CommandForm onSave={handleCreate} onCancel={() => setFormOpen(false)} />}

      {deletingCmd && (
        <ConfirmDialog
          title="Delete command?"
          message="This only works for commands that haven't been executed yet by the node."
          onConfirm={handleDelete}
          onCancel={() => setDeletingCmd(null)}
        />
      )}
    </div>
  );
}
