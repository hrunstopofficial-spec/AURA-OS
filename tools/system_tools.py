import os
import sys
import time
import socket
import datetime
import psutil
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.registry import aura_tool


@aura_tool(name="get_cpu_usage", category="server", description="Returns current CPU utilization percentage and core count.")
def get_cpu_usage() -> Dict[str, Any]:
    """Get real-time CPU telemetry."""
    cpu_pct = psutil.cpu_percent(interval=0.2)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    return {
        "cpu_percent": cpu_pct,
        "cores_logical": psutil.cpu_count(logical=True),
        "cores_physical": psutil.cpu_count(logical=False),
        "per_core_percent": per_cpu
    }


@aura_tool(name="get_memory_usage", category="server", description="Returns RAM and Virtual Memory metrics in MB and percent.")
def get_memory_usage() -> Dict[str, Any]:
    """Get real-time RAM and Swap metrics."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total_mb": round(mem.total / (1024 * 1024), 2),
        "available_mb": round(mem.available / (1024 * 1024), 2),
        "used_mb": round(mem.used / (1024 * 1024), 2),
        "percent": mem.percent,
        "swap_used_mb": round(swap.used / (1024 * 1024), 2),
        "swap_percent": swap.percent
    }


@aura_tool(name="get_disk_usage", category="server", description="Returns disk capacity, usage, and free space in GB for a drive.")
def get_disk_usage(drive: str = "C:\\") -> Dict[str, Any]:
    """Get disk storage telemetry for the specified drive path."""
    try:
        usage = psutil.disk_usage(drive)
        return {
            "drive": drive,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent": usage.percent
        }
    except Exception as e:
        return {"drive": drive, "error": str(e), "percent": 0.0}


@aura_tool(name="get_battery_status", category="server", description="Returns battery charge percentage, charger plug state, and remaining duration.")
def get_battery_status() -> Dict[str, Any]:
    """Get laptop battery and power telemetry."""
    battery = psutil.sensors_battery()
    if not battery:
        return {
            "has_battery": False,
            "battery_percent": 100.0,
            "is_charging": True,
            "status": "Desktop / AC Power (No Battery Detected)"
        }
    
    status = "Charging / Plugged in" if battery.power_plugged else "Discharging (On Battery)"
    return {
        "has_battery": True,
        "battery_percent": battery.percent,
        "is_charging": bool(battery.power_plugged),
        "secs_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
        "status": status
    }


@aura_tool(name="get_top_processes", category="server", description="Returns list of top resource-consuming processes sorted by memory or CPU.")
def get_top_processes(limit: int = 5, sort_by: str = "memory") -> List[Dict[str, Any]]:
    """Retrieve top running processes by resource consumption."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = p.info
            mem_mb = round(info['memory_info'].rss / (1024 * 1024), 2) if info.get('memory_info') else 0.0
            procs.append({
                "pid": info['pid'],
                "name": info['name'] or "unknown",
                "cpu_percent": info.get('cpu_percent') or 0.0,
                "memory_mb": mem_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by == "cpu":
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
    else:
        procs.sort(key=lambda x: x["memory_mb"], reverse=True)

    return procs[:limit]


@aura_tool(name="get_network_ping", category="server", description="Measures network connectivity and latency in milliseconds.")
def get_network_ping(host: str = "1.1.1.1", port: int = 53, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """Test outbound internet connection latency via TCP socket connect."""
    start = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        sock.connect((host, port))
        sock.close()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "online": True,
            "latency_ms": latency_ms,
            "target": f"{host}:{port}"
        }
    except Exception as e:
        return {
            "online": False,
            "latency_ms": -1,
            "target": f"{host}:{port}",
            "error": str(e)
        }


@aura_tool(name="get_system_vitals", category="server", description="Consolidated real-time system vitals snapshot (CPU, RAM, Disk, Battery, Net).")
def get_system_vitals() -> Dict[str, Any]:
    """Collect full telemetry snapshot of the machine."""
    cpu = get_cpu_usage()
    mem = get_memory_usage()
    disk = get_disk_usage("C:\\")
    battery = get_battery_status()
    net = get_network_ping()
    top_proc = get_top_processes(limit=3, sort_by="memory")

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu": cpu,
        "memory": mem,
        "disk": disk,
        "battery": battery,
        "network": net,
        "top_processes": top_proc
    }


@aura_tool(name="get_system_health_diagnosis", category="server", description="Provides in-depth AI health score (0-100), resource bottleneck analysis, and comparison with historical baseline.")
def get_system_health_diagnosis() -> Dict[str, Any]:
    """Collect full vitals, log snapshot to SQLite, and compute diagnostic health score."""
    from storage.memory.system_metrics import metrics_store
    from agents.analysis_engine import analysis_engine
    vitals = get_system_vitals()
    metrics_store.record_snapshot(vitals)
    delta = metrics_store.compute_telemetry_delta(vitals, hours=24.0)
    diagnosis = analysis_engine.analyze(vitals, delta)
    return diagnosis

