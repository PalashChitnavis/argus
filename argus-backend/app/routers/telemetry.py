from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.core.auth import get_current_node
from app.models.node import Node
from app.models.startup_data import StartupData
from app.models.installed_package import InstalledPackage
from app.models.one_minute_data import OneMinuteData
from app.models.new_process import NewProcess
from app.models.five_minute_data import FiveMinuteData
from app.models.network_connection import NetworkConnection
from app.models.recent_log import RecentLog
from app.models.auth_event import AuthEvent
from app.models.thirty_minute_data import ThirtyMinuteData
from app.models.network_interface import NetworkInterface
from app.models.dns_server import DnsServer
from app.models.routing_entry import RoutingEntry
from app.models.daily_data import DailyData
from app.models.daily_installed_package import DailyInstalledPackage
from app.schemas.telemetry import (
    StartupDataRequest, OneMinuteDataRequest, FiveMinuteDataRequest,
    ThirtyMinuteDataRequest, DailyDataRequest
)
from app.models.visited_site import VisitedSite

router = APIRouter()


@router.post("/startup-data", status_code=201)
def receive_startup_data(
    request: StartupDataRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    row = StartupData(node_id=node.id)
    if request.os_info:
        row.distro_name = request.os_info.distro_name
        row.distro_version = request.os_info.distro_version
        row.distro_codename = request.os_info.distro_codename
        row.distro_id = request.os_info.distro_id
        row.kernel_version = request.os_info.kernel_version
        row.architecture = request.os_info.architecture
    if request.hardware_info:
        row.cpu_cores_physical = request.hardware_info.cpu_cores_physical
        row.cpu_cores_logical = request.hardware_info.cpu_cores_logical
        row.ram_total_gb = request.hardware_info.ram_total_gb
        row.disk_total_gb = request.hardware_info.disk_total_gb
    db.add(row)
    db.flush()
    db.bulk_save_objects([
        InstalledPackage(startup_data_id=row.id, package_name=pkg)
        for pkg in (request.installed_packages or [])
    ])
    db.commit()
    return {"status": "ok"}


@router.post("/one-minute-data", status_code=201)
def receive_one_minute_data(
    request: OneMinuteDataRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    row = OneMinuteData(node_id=node.id)
    if request.cpu_usage:
        row.cpu_percent_used = request.cpu_usage.cpu_percent_used
    db.add(row)
    db.flush()
    db.bulk_save_objects([
        NewProcess(
            one_minute_data_id=row.id,
            pid=p.pid,
            create_time=p.create_time,
            name=p.name,
            username=p.username,
            cmdline=p.cmdline,
            status=p.status,
            cpu_percent=p.cpu_percent,
            memory_percent=p.memory_percent,
        )
        for p in (request.new_processes or [])
    ])
    db.commit()
    return {"status": "ok"}


def _none_str(val):
    """Convert the string 'None' that psutil emits to Python None."""
    if val == "None" or val == "":
        return None
    return val


@router.post("/five-minute-data", status_code=201)
def receive_five_minute_data(
    request: FiveMinuteDataRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    row = FiveMinuteData(node_id=node.id)
    if request.disk_usage:
        row.disk_used_gb = request.disk_usage.disk_used_gb
        row.disk_free_gb = request.disk_usage.disk_free_gb
        row.disk_percent_used = request.disk_usage.disk_percent_used
    if request.ram_usage:
        row.ram_used_gb = request.ram_usage.ram_used_gb
        row.ram_available_gb = request.ram_usage.ram_available_gb
        row.ram_percent_used = request.ram_usage.ram_percent_used
    if request.network_io:
        row.bytes_sent_mb = request.network_io.bytes_sent_mb
        row.bytes_recv_mb = request.network_io.bytes_recv_mb
    db.add(row)
    db.flush()

    db.bulk_save_objects([
        NetworkConnection(
            five_minute_data_id=row.id,
            local_ip=_none_str(c.local_ip),
            local_port=c.local_port,
            remote_ip=_none_str(c.remote_ip),
            remote_port=c.remote_port,
            status=c.status,
            pid=c.pid,
            process_name=_none_str(c.process_name),
        )
        for c in (request.connections or [])
    ])

    db.bulk_save_objects([
        RecentLog(five_minute_data_id=row.id, log_line=line)
        for line in (request.recent_logs or [])
    ])

    db.bulk_save_objects([
        AuthEvent(five_minute_data_id=row.id, log_line=line)
        for line in (request.auth_events or [])
    ])

    # most-visited domains (most_visited=1)
    db.bulk_save_objects([
        VisitedSite(
            five_minute_data_id=row.id,
            most_visited=1,
            domain=entry.domain,
            visit_count=entry.visit_count,
            last_visit_time=entry.last_visit_time,
            browsers=entry.browsers,
            title=entry.title,
        )
        for entry in (request.browser_history or [])
    ])

    # recently visited individual visits (most_visited=0)
    db.bulk_save_objects([
        VisitedSite(
            five_minute_data_id=row.id,
            most_visited=0,
            url=entry.url,
            domain=entry.domain,
            title=entry.title,
            last_visit_time=entry.last_visit_time,
            browser=entry.browser,
        )
        for entry in (request.recently_visited or [])
    ])

    db.commit()
    return {"status": "ok"}


@router.post("/thirty-minute-data", status_code=201)
def receive_thirty_minute_data(
    request: ThirtyMinuteDataRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    row = ThirtyMinuteData(node_id=node.id)
    if request.firewall_status:
        row.firewall_tool = request.firewall_status.firewall_tool
        row.firewall_active = request.firewall_status.firewall_active
    if request.disk_encryption:
        row.disk_encrypted = request.disk_encryption.disk_encrypted
    if request.ssh_config:
        row.root_login_permitted = request.ssh_config.root_login_permitted
        row.password_auth_permitted = request.ssh_config.password_auth_permitted
    if request.mac_status:
        row.mac_tool = request.mac_status.mac_tool
        row.mac_enabled = request.mac_status.mac_enabled
    db.add(row)
    db.flush()
    db.bulk_save_objects([
        NetworkInterface(
            thirty_minute_data_id=row.id,
            interface_name=i.interface_name,
            ipv4=i.ipv4,
            ipv6=i.ipv6,
            mac_address=i.mac_address,
        )
        for i in (request.interfaces or [])
    ])
    db.bulk_save_objects([
        DnsServer(thirty_minute_data_id=row.id, address=addr)
        for addr in (request.dns_servers or [])
    ])
    db.bulk_save_objects([
        RoutingEntry(thirty_minute_data_id=row.id, route=r)
        for r in (request.routing_table or [])
    ])
    db.commit()
    return {"status": "ok"}


@router.post("/daily-data", status_code=201)
def receive_daily_data(
    request: DailyDataRequest,
    db: Session = Depends(get_db),
    node: Node = Depends(get_current_node)
):
    row = DailyData(node_id=node.id)
    if request.os_info:
        row.distro_name = request.os_info.distro_name
        row.distro_version = request.os_info.distro_version
        row.distro_codename = request.os_info.distro_codename
        row.distro_id = request.os_info.distro_id
        row.kernel_version = request.os_info.kernel_version
        row.architecture = request.os_info.architecture
    if request.hardware_info:
        row.cpu_cores_physical = request.hardware_info.cpu_cores_physical
        row.cpu_cores_logical = request.hardware_info.cpu_cores_logical
        row.ram_total_gb = request.hardware_info.ram_total_gb
        row.disk_total_gb = request.hardware_info.disk_total_gb
    db.add(row)
    db.flush()
    db.bulk_save_objects([
        DailyInstalledPackage(daily_data_id=row.id, package_name=pkg)
        for pkg in (request.installed_packages or [])
    ])
    db.commit()
    return {"status": "ok"}