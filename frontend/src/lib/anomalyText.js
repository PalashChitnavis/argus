// Maps raw feature_name keys (from the backend's fixed FEATURE_NAMES list)
// to human-readable labels for the anomaly detail view.

const LABELS = {
  cpu_avg: 'CPU usage',
  ram_avg: 'RAM usage',
  disk_avg: 'Disk usage',
  net_sent_mb: 'Network sent (MB)',
  net_recv_mb: 'Network received (MB)',
  new_process_count: 'New processes',
  avg_process_cpu: 'Avg process CPU %',
  avg_process_mem: 'Avg process memory %',
  connection_count: 'Active connections',
  distinct_remote_ips: 'Distinct remote IPs',
  avg_remote_port_scaled: 'Avg remote port',
  new_site_visit_count: 'New site visits',
  distinct_domain_count: 'Distinct domains',
  system_log_count: 'System log lines',
  auth_event_count: 'Auth log lines',
};

export function featureLabel(name) {
  return LABELS[name] || name;
}

// avg_remote_port_scaled is stored divided by 1000 so it doesn't dominate
// the model's distance metric — undo that just for display.
export function featureDisplayValue(name, value) {
  if (name === 'avg_remote_port_scaled') return Math.round(value * 1000);
  return Math.round(value * 100) / 100;
}

export function zScoreDirection(z) {
  if (z > 0.3) return 'high';
  if (z < -0.3) return 'low';
  return 'normal';
}
