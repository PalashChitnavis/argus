"""
Anomaly detection over a node's recent telemetry.

Approach
--------
Telemetry lands in Postgres as separate per-collector tables at different
cadences (CPU every 1 min, RAM/disk/network/connections/logs every 5 min,
browser history every 10 min). To feed a single model, we bucket everything
into fixed 5-minute windows per node and build one feature vector per
window, aggregating whatever landed in that window from each table.

A fresh IsolationForest is fit per scan on that node's own recent windows
(no persisted model file — the "normal" baseline is always the node's own
recent behaviour, refit every scan). This mirrors the original telemetry
schema redesign philosophy: no cross-node state, everything scoped to a
single node's own history.

contamination is fixed at 0.1 (not "auto") so a handful of demo windows
don't get either all flagged or all ignored depending on chance.
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from statistics import mean, pstdev

from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest

from app.models.cpu_snapshot import CpuSnapshot
from app.models.ram_snapshot import RamSnapshot
from app.models.disk_snapshot import DiskSnapshot
from app.models.network_io_snapshot import NetworkIoSnapshot
from app.models.process_snapshot import ProcessSnapshot
from app.models.active_connection import ActiveConnection
from app.models.visited_site import VisitedSite
from app.models.system_log import SystemLog
from app.models.auth_event import AuthEvent

BUCKET_MINUTES = 5
MIN_WINDOWS_REQUIRED = 6  # need at least this many windows for IsolationForest to mean anything
CONTAMINATION = 0.1
TOP_CONTRIBUTING_FEATURES = 3

# Fixed feature order — every window vector follows this order, missing
# signals default to 0.0 (e.g. no new processes in a quiet window).
FEATURE_NAMES = [
    "cpu_avg",
    "ram_avg",
    "disk_avg",
    "net_sent_mb",
    "net_recv_mb",
    "new_process_count",
    "avg_process_cpu",
    "avg_process_mem",
    "connection_count",
    "distinct_remote_ips",
    "avg_remote_port_scaled",
    "new_site_visit_count",
    "distinct_domain_count",
    "system_log_count",
    "auth_event_count",
]


def _aware(dt: datetime) -> datetime:
    """Defensive: some drivers return naive datetimes even for tz-aware columns."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _bucket_start(dt: datetime) -> datetime:
    dt = _aware(dt)
    floored_minute = (dt.minute // BUCKET_MINUTES) * BUCKET_MINUTES
    return dt.replace(minute=floored_minute, second=0, microsecond=0)


def _extract_windows(db: Session, node_id: int, since: datetime) -> dict:
    """
    Returns {window_start: {feature_name: value}} built from raw rows.
    Uses running sums/lists per bucket, then reduces to final scalar
    features at the end (averages, counts, distinct counts).
    """
    raw = defaultdict(lambda: {
        "cpu_vals": [], "ram_vals": [], "disk_vals": [],
        "net_sent": 0.0, "net_recv": 0.0,
        "new_process_count": 0, "proc_cpu_vals": [], "proc_mem_vals": [],
        "connection_count": 0, "remote_ips": set(), "remote_ports": [],
        "new_site_visit_count": 0, "domains": set(),
        "system_log_count": 0, "auth_event_count": 0,
    })

    for row in db.query(CpuSnapshot).filter(CpuSnapshot.node_id == node_id, CpuSnapshot.received_at >= since):
        if row.cpu_percent_used is not None:
            raw[_bucket_start(row.received_at)]["cpu_vals"].append(row.cpu_percent_used)

    for row in db.query(RamSnapshot).filter(RamSnapshot.node_id == node_id, RamSnapshot.received_at >= since):
        if row.ram_percent_used is not None:
            raw[_bucket_start(row.received_at)]["ram_vals"].append(row.ram_percent_used)

    for row in db.query(DiskSnapshot).filter(DiskSnapshot.node_id == node_id, DiskSnapshot.received_at >= since):
        if row.disk_percent_used is not None:
            raw[_bucket_start(row.received_at)]["disk_vals"].append(row.disk_percent_used)

    for row in db.query(NetworkIoSnapshot).filter(NetworkIoSnapshot.node_id == node_id, NetworkIoSnapshot.received_at >= since):
        b = raw[_bucket_start(row.received_at)]
        b["net_sent"] += row.bytes_sent_mb or 0.0
        b["net_recv"] += row.bytes_recv_mb or 0.0

    for row in db.query(ProcessSnapshot).filter(ProcessSnapshot.node_id == node_id, ProcessSnapshot.received_at >= since):
        b = raw[_bucket_start(row.received_at)]
        b["new_process_count"] += 1
        if row.cpu_percent is not None:
            b["proc_cpu_vals"].append(row.cpu_percent)
        if row.memory_percent is not None:
            b["proc_mem_vals"].append(row.memory_percent)

    for row in db.query(ActiveConnection).filter(ActiveConnection.node_id == node_id, ActiveConnection.received_at >= since):
        b = raw[_bucket_start(row.received_at)]
        b["connection_count"] += 1
        if row.remote_ip:
            b["remote_ips"].add(row.remote_ip)
        if row.remote_port is not None:
            b["remote_ports"].append(row.remote_port)

    for row in db.query(VisitedSite).filter(
        VisitedSite.node_id == node_id, VisitedSite.received_at >= since, VisitedSite.most_visited == 0
    ):
        b = raw[_bucket_start(row.received_at)]
        b["new_site_visit_count"] += 1
        if row.domain:
            b["domains"].add(row.domain)

    for row in db.query(SystemLog).filter(SystemLog.node_id == node_id, SystemLog.received_at >= since):
        raw[_bucket_start(row.received_at)]["system_log_count"] += 1

    for row in db.query(AuthEvent).filter(AuthEvent.node_id == node_id, AuthEvent.received_at >= since):
        raw[_bucket_start(row.received_at)]["auth_event_count"] += 1

    windows = {}
    for bucket_start, b in raw.items():
        windows[bucket_start] = {
            "cpu_avg": mean(b["cpu_vals"]) if b["cpu_vals"] else 0.0,
            "ram_avg": mean(b["ram_vals"]) if b["ram_vals"] else 0.0,
            "disk_avg": mean(b["disk_vals"]) if b["disk_vals"] else 0.0,
            "net_sent_mb": b["net_sent"],
            "net_recv_mb": b["net_recv"],
            "new_process_count": float(b["new_process_count"]),
            "avg_process_cpu": mean(b["proc_cpu_vals"]) if b["proc_cpu_vals"] else 0.0,
            "avg_process_mem": mean(b["proc_mem_vals"]) if b["proc_mem_vals"] else 0.0,
            "connection_count": float(b["connection_count"]),
            "distinct_remote_ips": float(len(b["remote_ips"])),
            # scaled down so raw port numbers (0-65535) don't dominate the
            # distance metric next to percentages and small counts
            "avg_remote_port_scaled": (mean(b["remote_ports"]) / 1000) if b["remote_ports"] else 0.0,
            "new_site_visit_count": float(b["new_site_visit_count"]),
            "distinct_domain_count": float(len(b["domains"])),
            "system_log_count": float(b["system_log_count"]),
            "auth_event_count": float(b["auth_event_count"]),
        }
    return windows


def _top_contributing_features(window_features: dict, all_windows: list[dict]) -> list[dict]:
    """
    For a flagged window, rank features by |z-score| against the mean/stdev
    of that same feature across all scanned windows for this node. Gives a
    human-readable "why" for each flagged window.
    """
    contributions = []
    for name in FEATURE_NAMES:
        population = [w[name] for w in all_windows]
        pop_mean = mean(population)
        pop_std = pstdev(population)
        value = window_features[name]
        z = (value - pop_mean) / pop_std if pop_std > 0 else 0.0
        contributions.append({"feature": name, "value": round(value, 3), "z_score": round(z, 3)})
    contributions.sort(key=lambda c: abs(c["z_score"]), reverse=True)
    return contributions[:TOP_CONTRIBUTING_FEATURES]


def run_anomaly_scan(db: Session, node_id: int, hours: int) -> dict:
    """
    Extracts feature windows for the given lookback, fits a fresh
    IsolationForest, and returns (scan_start, scan_end, windows, flagged)
    where `flagged` is a list of (window_start, window_end, score, features,
    contributing_features) tuples. Does not touch the DB — the router owns
    persistence so this function stays easy to test.
    """
    scan_end = datetime.now(timezone.utc)
    scan_start = scan_end - timedelta(hours=hours)

    windows_by_start = _extract_windows(db, node_id, scan_start)
    window_count = len(windows_by_start)

    if window_count < MIN_WINDOWS_REQUIRED:
        return {
            "scan_start": scan_start,
            "scan_end": scan_end,
            "window_count": window_count,
            "flagged": [],
            "message": (
                f"Only {window_count} telemetry window(s) available in the last {hours}h "
                f"(need at least {MIN_WINDOWS_REQUIRED}). Let more data collect and re-scan."
            ),
        }

    sorted_starts = sorted(windows_by_start.keys())
    all_windows = [windows_by_start[s] for s in sorted_starts]
    matrix = [[w[name] for name in FEATURE_NAMES] for w in all_windows]

    model = IsolationForest(n_estimators=100, contamination=CONTAMINATION, random_state=42)
    model.fit(matrix)
    scores = model.decision_function(matrix)  # lower = more anomalous
    predictions = model.predict(matrix)  # -1 anomaly, 1 normal

    flagged = []
    for window_start, window_features, score, pred in zip(sorted_starts, all_windows, scores, predictions):
        if pred == -1:
            flagged.append({
                "window_start": window_start,
                "window_end": window_start + timedelta(minutes=BUCKET_MINUTES),
                "anomaly_score": float(score),
                "features": window_features,
                "contributing_features": _top_contributing_features(window_features, all_windows),
            })

    return {
        "scan_start": scan_start,
        "scan_end": scan_end,
        "window_count": window_count,
        "flagged": flagged,
        "message": None,
    }
