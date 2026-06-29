import { useState } from 'react';

const RULE_TYPES = ['port', 'ip', 'ip_port', 'domain', 'bandwidth', 'user_port'];
const RULE_TYPE_LABELS = {
  port: 'Port — block/allow a specific port',
  ip: 'IP address — block/allow a specific device',
  ip_port: 'IP + port — block/allow one device on one port',
  domain: 'Domain — block/allow a website',
  bandwidth: 'Bandwidth limit — cap network speed',
  user_port: 'Per-user port — block/allow a port for one user',
};

const ACTIONS_BY_TYPE = {
  port: ['allow', 'deny'],
  ip: ['allow', 'deny'],
  ip_port: ['allow', 'deny'],
  domain: ['block', 'unblock'],
  bandwidth: ['set', 'remove'],
  user_port: ['block', 'unblock'],
};

function defaultParams(ruleType) {
  switch (ruleType) {
    case 'port': return { port: 22, protocol: 'tcp', direction: 'in' };
    case 'ip': return { ip: '', direction: 'in' };
    case 'ip_port': return { ip: '', port: 443, protocol: 'tcp', direction: 'in' };
    case 'domain': return { domain: '' };
    case 'bandwidth': return { rate_mbit: 1, interface: 'eth0' };
    case 'user_port': return { username: '', port: 443, protocol: 'tcp' };
    default: return {};
  }
}

export default function FirewallRuleForm({ initial, onSave, onCancel }) {
  const isEdit = Boolean(initial);
  const [ruleType, setRuleType] = useState(initial?.rule_type || 'port');
  const [action, setAction] = useState(initial?.action || ACTIONS_BY_TYPE[initial?.rule_type || 'port'][0]);
  const [params, setParams] = useState(initial?.params || defaultParams(initial?.rule_type || 'port'));
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const [description, setDescription] = useState(initial?.description || '');
  const [useSchedule, setUseSchedule] = useState(Boolean(initial?.schedule));
  const [startTime, setStartTime] = useState(initial?.schedule?.start_time || '09:00');
  const [endTime, setEndTime] = useState(initial?.schedule?.end_time || '17:00');
  const [saving, setSaving] = useState(false);

  function handleTypeChange(newType) {
    setRuleType(newType);
    setAction(ACTIONS_BY_TYPE[newType][0]);
    setParams(defaultParams(newType));
  }

  function setParam(key, value) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    const payload = {
      rule_type: ruleType,
      action,
      params: normalizeParams(ruleType, params),
      enabled,
      description: description || null,
      schedule: useSchedule ? { start_time: startTime, end_time: endTime } : null,
    };
    try {
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  }

  function normalizeParams(type, p) {
    if (type === 'port') return { ...p, port: Number(p.port) };
    if (type === 'ip_port') return { ...p, port: Number(p.port) };
    if (type === 'bandwidth') return { ...p, rate_mbit: Number(p.rate_mbit) };
    if (type === 'user_port') return { ...p, port: Number(p.port) };
    return p;
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <form className="modal" onSubmit={handleSubmit}>
        <div className="modal-title">
          {isEdit ? `Edit rule #${initial.id}` : 'New firewall rule'}
        </div>

        <div className="field-row">
          <div className="field">
            <label>Rule type</label>
            <select value={ruleType} onChange={(e) => handleTypeChange(e.target.value)}>
              {RULE_TYPES.map((t) => <option key={t} value={t}>{RULE_TYPE_LABELS[t]}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Action</label>
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              {ACTIONS_BY_TYPE[ruleType].map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>

        {ruleType === 'port' && (
          <>
            <div className="field-row">
              <div className="field">
                <label>Port</label>
                <input type="number" min={1} max={65535} value={params.port} onChange={(e) => setParam('port', e.target.value)} required />
              </div>
              <div className="field">
                <label>Protocol</label>
                <select value={params.protocol} onChange={(e) => setParam('protocol', e.target.value)}>
                  <option value="tcp">tcp</option>
                  <option value="udp">udp</option>
                  <option value="any">any</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label>Direction</label>
              <select value={params.direction} onChange={(e) => setParam('direction', e.target.value)}>
                <option value="in">in</option>
                <option value="out">out</option>
              </select>
            </div>
          </>
        )}

        {ruleType === 'ip' && (
          <>
            <div className="field">
              <label>IP address / CIDR</label>
              <input type="text" placeholder="192.168.1.50" value={params.ip} onChange={(e) => setParam('ip', e.target.value)} required />
            </div>
            <div className="field">
              <label>Direction</label>
              <select value={params.direction} onChange={(e) => setParam('direction', e.target.value)}>
                <option value="in">in</option>
                <option value="out">out</option>
              </select>
            </div>
          </>
        )}

        {ruleType === 'ip_port' && (
          <>
            <div className="field">
              <label>IP address / CIDR</label>
              <input type="text" placeholder="10.0.0.5" value={params.ip} onChange={(e) => setParam('ip', e.target.value)} required />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Port</label>
                <input type="number" min={1} max={65535} value={params.port} onChange={(e) => setParam('port', e.target.value)} required />
              </div>
              <div className="field">
                <label>Protocol</label>
                <select value={params.protocol} onChange={(e) => setParam('protocol', e.target.value)}>
                  <option value="tcp">tcp</option>
                  <option value="udp">udp</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label>Direction</label>
              <select value={params.direction} onChange={(e) => setParam('direction', e.target.value)}>
                <option value="in">in</option>
                <option value="out">out</option>
              </select>
            </div>
          </>
        )}

        {ruleType === 'domain' && (
          <div className="field">
            <label>Domain</label>
            <input type="text" placeholder="facebook.com" value={params.domain} onChange={(e) => setParam('domain', e.target.value)} required />
          </div>
        )}

        {ruleType === 'bandwidth' && (
          <div className="field-row">
            <div className="field">
              <label>Rate (Mbps)</label>
              <input type="number" step="0.1" min={0.1} value={params.rate_mbit} onChange={(e) => setParam('rate_mbit', e.target.value)} required />
            </div>
            <div className="field">
              <label>Interface</label>
              <input type="text" placeholder="eth0" value={params.interface} onChange={(e) => setParam('interface', e.target.value)} required />
            </div>
          </div>
        )}

        {ruleType === 'user_port' && (
          <>
            <div className="field">
              <label>Username</label>
              <input type="text" placeholder="palash" value={params.username} onChange={(e) => setParam('username', e.target.value)} required />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Port</label>
                <input type="number" min={1} max={65535} value={params.port} onChange={(e) => setParam('port', e.target.value)} required />
              </div>
              <div className="field">
                <label>Protocol</label>
                <select value={params.protocol} onChange={(e) => setParam('protocol', e.target.value)}>
                  <option value="tcp">tcp</option>
                  <option value="udp">udp</option>
                </select>
              </div>
            </div>
          </>
        )}

        <div className="field">
          <label>Description (optional)</label>
          <input type="text" placeholder="Block HTTP" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="field checkbox-field">
          <input type="checkbox" id="useSchedule" checked={useSchedule} onChange={(e) => setUseSchedule(e.target.checked)} />
          <label htmlFor="useSchedule" style={{ margin: 0, textTransform: 'none' }}>Time-based schedule</label>
        </div>

        {useSchedule && (
          <div className="field-row">
            <div className="field">
              <label>Start time</label>
              <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
            </div>
            <div className="field">
              <label>End time</label>
              <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
            </div>
          </div>
        )}

        <div className="field checkbox-field">
          <input type="checkbox" id="enabled" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          <label htmlFor="enabled" style={{ margin: 0, textTransform: 'none' }}>Enabled</label>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create rule'}
          </button>
        </div>
      </form>
    </div>
  );
}
