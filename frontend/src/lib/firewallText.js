// Turns a firewall rule's raw rule_type/action/params into a plain-English
// sentence, so the firewall page reads like "block port 80" instead of
// exposing the underlying type/action/params shape directly.

const ACTION_VERBS = {
  allow: 'Allow',
  deny: 'Block',
  block: 'Block',
  unblock: 'Allow',
  set: 'Limit',
  remove: 'Remove limit on',
};

export function describeRule(rule) {
  const p = rule.params || {};
  const verb = ACTION_VERBS[rule.action] || rule.action;

  switch (rule.rule_type) {
    case 'port':
      return `${verb} ${p.direction === 'out' ? 'outgoing' : 'incoming'} traffic on port ${p.port} (${p.protocol || 'tcp'})`;
    case 'ip':
      return `${verb} all traffic ${p.direction === 'out' ? 'to' : 'from'} ${p.ip}`;
    case 'ip_port':
      return `${verb} traffic ${p.direction === 'out' ? 'to' : 'from'} ${p.ip} on port ${p.port} (${p.protocol || 'tcp'})`;
    case 'domain':
      return `${verb} access to ${p.domain}`;
    case 'bandwidth':
      return rule.action === 'remove'
        ? `Remove the bandwidth limit on ${p.interface}`
        : `Limit ${p.interface} to ${p.rate_mbit} Mbps`;
    case 'user_port':
      return `${verb} user "${p.username}" from using port ${p.port} (${p.protocol || 'tcp'})`;
    default:
      return `${rule.rule_type} · ${rule.action}`;
  }
}

export function ruleTypeLabel(ruleType) {
  return {
    port: 'Port rule',
    ip: 'IP rule',
    ip_port: 'IP + port rule',
    domain: 'Domain block',
    bandwidth: 'Bandwidth limit',
    user_port: 'Per-user rule',
  }[ruleType] || ruleType;
}

// Short technical line shown under the plain-English description, for
// people who want the exact params at a glance.
export function paramsSummary(rule) {
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
