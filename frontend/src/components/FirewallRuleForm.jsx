import { useState } from 'react';

const RULE_TYPES = ['port', 'ip', 'ip_port', 'domain', 'bandwidth', 'user_port'];

const RULE_TYPE_META = {
  port:       { label: 'Port rule', icon: '⚡', desc: 'Block or allow a TCP/UDP port' },
  ip:         { label: 'IP rule', icon: '🔒', desc: 'Block or allow an IP address or range' },
  ip_port:    { label: 'IP + Port', icon: '🎯', desc: 'Block/allow one IP on a specific port' },
  domain:     { label: 'Domain block', icon: '🌐', desc: 'Redirect a domain to 0.0.0.0 via /etc/hosts' },
  bandwidth:  { label: 'Bandwidth limit', icon: '📊', desc: 'Cap network speed on an interface' },
  user_port:  { label: 'Per-user rule', icon: '👤', desc: 'Block/allow a port for one system user' },
};

const ACTIONS_BY_TYPE = {
  port:       ['allow', 'deny'],
  ip:         ['allow', 'deny'],
  ip_port:    ['allow', 'deny'],
  domain:     ['block', 'unblock'],
  bandwidth:  ['set', 'remove'],
  user_port:  ['block', 'unblock'],
};

const ACTION_LABELS = {
  allow: 'Allow ✓',
  deny: 'Deny ✗',
  block: 'Block ✗',
  unblock: 'Unblock ✓',
  set: 'Set limit',
  remove: 'Remove limit',
};

function defaultParams(ruleType) {
  switch (ruleType) {
    case 'port':      return { port: 22, protocol: 'tcp', direction: 'in' };
    case 'ip':        return { ip: '', direction: 'in' };
    case 'ip_port':   return { ip: '', port: 443, protocol: 'tcp', direction: 'in' };
    case 'domain':    return { domain: '' };
    case 'bandwidth': return { rate_mbit: 1, interface: 'eth0' };
    case 'user_port': return { username: '', port: 443, protocol: 'tcp' };
    default:          return {};
  }
}

function normalizeParams(type, p) {
  if (type === 'port')       return { ...p, port: Number(p.port) };
  if (type === 'ip_port')    return { ...p, port: Number(p.port) };
  if (type === 'bandwidth')  return { ...p, rate_mbit: Number(p.rate_mbit) };
  if (type === 'user_port')  return { ...p, port: Number(p.port) };
  return p;
}

export default function FirewallRuleForm({ initial, onSave, onCancel }) {
  const isEdit = Boolean(initial);

  const [ruleType, setRuleType]       = useState(initial?.rule_type || 'port');
  const [action, setAction]           = useState(initial?.action || ACTIONS_BY_TYPE[initial?.rule_type || 'port'][0]);
  const [params, setParams]           = useState(initial?.params || defaultParams(initial?.rule_type || 'port'));
  const [enabled, setEnabled]         = useState(initial?.enabled ?? true);
  const [description, setDescription] = useState(initial?.description || '');
  const [useSchedule, setUseSchedule] = useState(Boolean(initial?.schedule));
  const [startTime, setStartTime]     = useState(initial?.schedule?.start_time || '09:00');
  const [endTime, setEndTime]         = useState(initial?.schedule?.end_time || '17:00');
  const [saving, setSaving]           = useState(false);

  function handleTypeChange(newType) {
    setRuleType(newType);
    setAction(ACTIONS_BY_TYPE[newType][0]);
    setParams(defaultParams(newType));
  }

  function setParam(key, value) {
    setParams(p => ({ ...p, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    const payload = {
      rule_type: ruleType,
      action,
      params: normalizeParams(ruleType, params),
      enabled,
      description: description.trim() || null,
      schedule: useSchedule ? { start_time: startTime, end_time: endTime } : null,
    };
    try {
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  }

  const meta = RULE_TYPE_META[ruleType];
  const actions = ACTIONS_BY_TYPE[ruleType];
  const isDeny = action === 'deny' || action === 'block';

  return (
    <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onCancel()}>
      <form className="modal" onSubmit={handleSubmit} style={{ maxWidth: 520 }}>

        {/* Header */}
        <div className="modal-title" style={{ marginBottom: 4 }}>
          {isEdit ? `Edit rule #${initial.id}` : 'New firewall rule'}
        </div>
        <div className="text-dim" style={{ fontSize: 12, marginBottom: 20 }}>
          {meta.icon} {meta.desc}
        </div>

        {/* Rule type selector */}
        {!isEdit && (
          <div className="field" style={{ marginBottom: 16 }}>
            <label>Rule type</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {RULE_TYPES.map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => handleTypeChange(t)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 5,
                    border: `1px solid ${ruleType === t ? 'var(--green)' : 'var(--border)'}`,
                    background: ruleType === t ? 'rgba(95,217,122,0.08)' : 'var(--bg)',
                    color: ruleType === t ? 'var(--green)' : 'var(--text-dim)',
                    fontSize: 12,
                    fontFamily: 'var(--sans)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.1s',
                  }}
                >
                  <span style={{ marginRight: 5 }}>{RULE_TYPE_META[t].icon}</span>
                  {RULE_TYPE_META[t].label}
                </button>
              ))}
            </div>
          </div>
        )}

        {isEdit && (
          <div className="field" style={{ marginBottom: 16 }}>
            <label>Rule type</label>
            <div style={{ padding: '7px 10px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 5, fontSize: 13, color: 'var(--text-dim)' }}>
              {meta.icon} {meta.label}
            </div>
          </div>
        )}

        {/* Action */}
        <div className="field">
          <label>Action</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {actions.map(a => (
              <button
                key={a}
                type="button"
                onClick={() => setAction(a)}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: 5,
                  border: `1px solid ${action === a ? (a === 'deny' || a === 'block' ? 'var(--red)' : 'var(--green)') : 'var(--border)'}`,
                  background: action === a
                    ? (a === 'deny' || a === 'block' ? 'rgba(224,82,77,0.1)' : 'rgba(95,217,122,0.08)')
                    : 'var(--bg)',
                  color: action === a
                    ? (a === 'deny' || a === 'block' ? 'var(--red)' : 'var(--green)')
                    : 'var(--text-dim)',
                  fontSize: 12.5,
                  fontWeight: 500,
                  fontFamily: 'var(--sans)',
                  cursor: 'pointer',
                  transition: 'all 0.1s',
                }}
              >
                {ACTION_LABELS[a] || a}
              </button>
            ))}
          </div>
        </div>

        {/* Separator */}
        <div style={{ borderTop: '1px solid var(--border)', margin: '16px 0' }} />

        {/* Params by rule type */}
        {ruleType === 'port' && (
          <div className="field-row">
            <div className="field">
              <label>Port</label>
              <input type="number" min={1} max={65535} value={params.port}
                onChange={e => setParam('port', e.target.value)} required />
            </div>
            <div className="field">
              <label>Protocol</label>
              <select value={params.protocol} onChange={e => setParam('protocol', e.target.value)}>
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
                <option value="any">Any</option>
              </select>
            </div>
            <div className="field">
              <label>Direction</label>
              <select value={params.direction} onChange={e => setParam('direction', e.target.value)}>
                <option value="in">Inbound</option>
                <option value="out">Outbound</option>
              </select>
            </div>
          </div>
        )}

        {ruleType === 'ip' && (
          <div className="field-row">
            <div className="field" style={{ flex: 2 }}>
              <label>IP address / CIDR</label>
              <input type="text" placeholder="192.168.1.50 or 10.0.0.0/8"
                value={params.ip} onChange={e => setParam('ip', e.target.value)} required />
            </div>
            <div className="field">
              <label>Direction</label>
              <select value={params.direction} onChange={e => setParam('direction', e.target.value)}>
                <option value="in">Inbound</option>
                <option value="out">Outbound</option>
              </select>
            </div>
          </div>
        )}

        {ruleType === 'ip_port' && (
          <>
            <div className="field">
              <label>IP address / CIDR</label>
              <input type="text" placeholder="10.0.0.5"
                value={params.ip} onChange={e => setParam('ip', e.target.value)} required />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Port</label>
                <input type="number" min={1} max={65535} value={params.port}
                  onChange={e => setParam('port', e.target.value)} required />
              </div>
              <div className="field">
                <label>Protocol</label>
                <select value={params.protocol} onChange={e => setParam('protocol', e.target.value)}>
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
              </div>
              <div className="field">
                <label>Direction</label>
                <select value={params.direction} onChange={e => setParam('direction', e.target.value)}>
                  <option value="in">Inbound</option>
                  <option value="out">Outbound</option>
                </select>
              </div>
            </div>
          </>
        )}

        {ruleType === 'domain' && (
          <div className="field">
            <label>Domain name</label>
            <input type="text" placeholder="facebook.com"
              value={params.domain} onChange={e => setParam('domain', e.target.value)} required />
            <div className="text-dim" style={{ fontSize: 11, marginTop: 4 }}>
              Both the bare domain and www. variant will be blocked in /etc/hosts
            </div>
          </div>
        )}

        {ruleType === 'bandwidth' && (
          <div className="field-row">
            <div className="field">
              <label>Rate limit (Mbps)</label>
              <input type="number" step="0.1" min={0.1} value={params.rate_mbit}
                onChange={e => setParam('rate_mbit', e.target.value)} required />
            </div>
            <div className="field">
              <label>Interface</label>
              <input type="text" placeholder="eth0" value={params.interface}
                onChange={e => setParam('interface', e.target.value)} required />
            </div>
          </div>
        )}

        {ruleType === 'user_port' && (
          <>
            <div className="field">
              <label>System username</label>
              <input type="text" placeholder="palash"
                value={params.username} onChange={e => setParam('username', e.target.value)} required />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Port</label>
                <input type="number" min={1} max={65535} value={params.port}
                  onChange={e => setParam('port', e.target.value)} required />
              </div>
              <div className="field">
                <label>Protocol</label>
                <select value={params.protocol} onChange={e => setParam('protocol', e.target.value)}>
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
              </div>
            </div>
          </>
        )}

        {/* Separator */}
        <div style={{ borderTop: '1px solid var(--border)', margin: '16px 0' }} />

        {/* Optional fields */}
        <div className="field">
          <label>Description <span style={{ color: 'var(--text-faint)', fontWeight: 400 }}>(optional)</span></label>
          <input type="text" placeholder="e.g. Block HTTP traffic from LAN"
            value={description} onChange={e => setDescription(e.target.value)} />
        </div>

        {/* Schedule */}
        <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden', marginTop: 4 }}>
          <div
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', cursor: 'pointer', userSelect: 'none' }}
            onClick={() => setUseSchedule(s => !s)}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>⏱ Time-based schedule</div>
              <div className="text-dim" style={{ fontSize: 11.5, marginTop: 2 }}>
                Apply rule only between two times each day
              </div>
            </div>
            <div style={{
              width: 36, height: 20, borderRadius: 10,
              background: useSchedule ? 'var(--green)' : 'var(--border-bright)',
              position: 'relative', transition: 'background 0.2s',
            }}>
              <div style={{
                position: 'absolute', top: 3, left: useSchedule ? 18 : 3,
                width: 14, height: 14, borderRadius: '50%',
                background: 'white', transition: 'left 0.2s',
              }} />
            </div>
          </div>

          {useSchedule && (
            <div style={{ padding: '0 14px 14px', borderTop: '1px solid var(--border)' }}>
              <div className="field-row" style={{ marginTop: 12 }}>
                <div className="field">
                  <label>Start time (24h)</label>
                  <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} />
                </div>
                <div className="field">
                  <label>End time (24h)</label>
                  <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} />
                </div>
              </div>
              <div className="text-dim" style={{ fontSize: 11, marginTop: 4 }}>
                The agent evaluates the window every 10 s — rule applies when the clock enters the window and is reversed when it leaves.
              </div>
            </div>
          )}
        </div>

        {/* Enabled toggle */}
        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, padding: '10px 14px', border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer' }}
          onClick={() => setEnabled(v => !v)}
        >
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Enabled</div>
            <div className="text-dim" style={{ fontSize: 11.5, marginTop: 2 }}>Disabled rules are saved but not applied to the node</div>
          </div>
          <div style={{
            width: 36, height: 20, borderRadius: 10,
            background: enabled ? 'var(--green)' : 'var(--border-bright)',
            position: 'relative', transition: 'background 0.2s',
          }}>
            <div style={{
              position: 'absolute', top: 3, left: enabled ? 18 : 3,
              width: 14, height: 14, borderRadius: '50%',
              background: 'white', transition: 'left 0.2s',
            }} />
          </div>
        </div>

        <div className="modal-actions" style={{ marginTop: 20 }}>
          <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create rule'}
          </button>
        </div>
      </form>
    </div>
  );
}
