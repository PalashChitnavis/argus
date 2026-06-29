import { useState } from 'react';

const COLLECTORS = [
  'network_interfaces',
  'active_connections',
  'firewall_status',
  'installed_packages',
  'resource_usage',
  'logs',
];

const RULE_TYPES = ['port', 'ip', 'ip_port', 'domain', 'bandwidth', 'user_port'];

export default function CommandForm({ onSave, onCancel }) {
  const [type, setType] = useState('refresh');
  const [saving, setSaving] = useState(false);

  // refresh
  const [collector, setCollector] = useState(COLLECTORS[0]);

  // enforce
  const [ruleType, setRuleType] = useState('port');
  const [action, setAction] = useState('allow');
  const [paramsJson, setParamsJson] = useState('{\n  "port": 22,\n  "protocol": "tcp",\n  "direction": "in"\n}');

  // delete-rule
  const [delRuleType, setDelRuleType] = useState('firewall');
  const [delRuleNumber, setDelRuleNumber] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      if (type === 'refresh') {
        await onSave('refresh', { collector });
      } else if (type === 'enforce') {
        let params;
        try {
          params = JSON.parse(paramsJson);
        } catch {
          throw new Error('Params must be valid JSON');
        }
        await onSave('enforce', { rule_type: ruleType, action, params });
      } else if (type === 'delete-rule') {
        await onSave('delete-rule', {
          rule_type: delRuleType,
          rule_number: delRuleNumber ? Number(delRuleNumber) : undefined,
        });
      } else if (type === 'get-rules') {
        await onSave('get-rules', {});
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <form className="modal" onSubmit={handleSubmit}>
        <div className="modal-title">New command</div>

        <div className="field">
          <label>Command type</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="refresh">refresh — pull fresh collector data</option>
            <option value="enforce">enforce — apply a rule</option>
            <option value="delete-rule">delete_rule — remove an applied rule</option>
            <option value="get-rules">get_rules — fetch enforcement state</option>
          </select>
        </div>

        {type === 'refresh' && (
          <div className="field">
            <label>Collector</label>
            <select value={collector} onChange={(e) => setCollector(e.target.value)}>
              {COLLECTORS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}

        {type === 'enforce' && (
          <>
            <div className="field-row">
              <div className="field">
                <label>Rule type</label>
                <select value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                  {RULE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Action</label>
                <input type="text" value={action} onChange={(e) => setAction(e.target.value)} placeholder="allow / deny / block…" />
              </div>
            </div>
            <div className="field">
              <label>Params (JSON)</label>
              <textarea rows={5} value={paramsJson} onChange={(e) => setParamsJson(e.target.value)} className="mono" />
              <div className="field-hint">Use the same shape shown on the Firewall Rules form for this rule type.</div>
            </div>
          </>
        )}

        {type === 'delete-rule' && (
          <div className="field-row">
            <div className="field">
              <label>Rule type</label>
              <input type="text" value={delRuleType} onChange={(e) => setDelRuleType(e.target.value)} />
            </div>
            <div className="field">
              <label>Rule number (optional)</label>
              <input type="number" value={delRuleNumber} onChange={(e) => setDelRuleNumber(e.target.value)} />
            </div>
          </div>
        )}

        {type === 'get-rules' && (
          <p className="text-dim" style={{ fontSize: 12.5 }}>
            This queues a command asking the node to report its full current enforcement state. No parameters needed.
          </p>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Queuing…' : 'Queue command'}
          </button>
        </div>
      </form>
    </div>
  );
}
