"""
System metrics collectors.

Pure standard-library collectors that read kernel and /proc data where
available and degrade gracefully to `None` on platforms or permission
levels where a value cannot be read. Every collector is a small pure
function that never raises.

All values are returned in a flat dict keyed by snake_case names so the
optimization rules engine can stay data-driven.
"""

from __future__ import annotations

import os
import platform
import shutil
import time
from typing import Optional


def _read_int(path: str) -> Optional[int]:
    """Read a single integer from a sysfs/proc file. Returns None on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return int(handle.read().strip().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _read_text(path: str) -> Optional[str]:
    """Read a whole file as text. Returns None on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return None


def collect() -> dict:
    """Collect all metrics into a single flat dict."""
    metrics: dict = {
        "platform": platform.system(),
        "release": platform.release(),
        "python_version": platform.python_version(),
        "cores": os.cpu_count() or None,
        "hostname": platform.node(),
        "arch": platform.machine(),
    }
    metrics.update(_memory())
    metrics.update(_load())
    metrics.update(_disk())
    metrics.update(_kernel_tuning())
    metrics.update(_uptime())
    metrics.update(_cpu_governor())
    metrics.update(_transparent_hugepages())
    metrics.update(_journald())
    return metrics


def _memory() -> dict:
    if platform.system() != "Linux":
        return {
            "mem_total_mb": None,
            "mem_available_mb": None,
            "swap_total_mb": None,
            "swap_free_mb": None,
            "mem_available_percent": None,
        }
    meminfo = _read_text("/proc/meminfo") or ""
    fields: dict = {}
    for line in meminfo.splitlines():
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip().split()[0] if parts[1].strip() else "0"
            try:
                fields[key] = int(value)
            except ValueError:
                pass
    total_kb = fields.get("MemTotal")
    avail_kb = fields.get("MemAvailable", fields.get("MemFree"))
    swap_total_kb = fields.get("SwapTotal")
    swap_free_kb = fields.get("SwapFree")

    def to_mb(kb: Optional[int]) -> Optional[int]:
        return round(kb / 1024) if kb is not None else None

    available_percent = (
        round(avail_kb / total_kb * 100) if total_kb and avail_kb else None
    )
    return {
        "mem_total_mb": to_mb(total_kb),
        "mem_available_mb": to_mb(avail_kb),
        "swap_total_mb": to_mb(swap_total_kb),
        "swap_free_mb": to_mb(swap_free_kb),
        "mem_available_percent": available_percent,
    }


def _load() -> dict:
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        return {"load1": None, "load5": None, "load15": None}
    return {"load1": round(load1, 2), "load5": round(load5, 2), "load15": round(load15, 2)}


def _disk() -> dict:
    """Root filesystem usage in percent and GB."""
    try:
        usage = shutil.disk_usage("/")
        total_gb = round(usage.total / (1024**3), 1)
        free_gb = round(usage.free / (1024**3), 1)
        used_percent = round(usage.used / usage.total * 100)
    except OSError:
        return {"disk_total_gb": None, "disk_free_gb": None, "disk_used_percent": None}
    return {
        "disk_total_gb": total_gb,
        "disk_free_gb": free_gb,
        "disk_used_percent": used_percent,
    }


def _uptime() -> dict:
    if platform.system() == "Linux":
        uptime_text = _read_text("/proc/uptime")
        if uptime_text:
            try:
                return {"uptime_days": round(float(uptime_text.split()[0]) / 86400, 1)}
            except (ValueError, IndexError):
                pass
    return {"uptime_days": None}


def _kernel_tuning() -> dict:
    if platform.system() != "Linux":
        return {
            "vm_swappiness": None,
            "vm_overcommit_memory": None,
            "tcp_congestion_control": None,
            "ip_forward": None,
            "vm_dirty_ratio": None,
        }
    return {
        "vm_swappiness": _read_int("/proc/sys/vm/swappiness"),
        "vm_overcommit_memory": _read_int("/proc/sys/vm/overcommit_memory"),
        "tcp_congestion_control": _read_text("/proc/sys/net/ipv4/tcp_congestion_control"),
        "ip_forward": _read_int("/proc/sys/net/ipv4/ip_forward"),
        "vm_dirty_ratio": _read_int("/proc/sys/vm/dirty_ratio"),
    }


def _cpu_governor() -> dict:
    if platform.system() != "Linux":
        return {"cpu_governor": None}
    return {"cpu_governor": _read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")}


def _transparent_hugepages() -> dict:
    if platform.system() != "Linux":
        return {"thp_mode": None}
    raw = _read_text("/sys/kernel/mm/transparent_hugepage/enabled")
    if raw is None:
        return {"thp_mode": None}
    for word in raw.split():
        if word.startswith("["):
            return {"thp_mode": word.strip("[]")}
    return {"thp_mode": raw.split()[0] if raw else None}


def _journald() -> dict:
    """Parse SystemMaxUse from journald config, if present."""
    if platform.system() != "Linux":
        return {"journald_system_max_use": None}
    raw = _read_text("/etc/systemd/journald.conf")
    if raw is None:
        return {"journald_system_max_use": None}
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("SystemMaxUse=") and not stripped.startswith("#"):
            return {"journald_system_max_use": stripped.split("=", 1)[1]}
    return {"journald_system_max_use": None}


def format_uptime(days: Optional[float]) -> str:
    if days is None:
        return "unknown"
    if days < 1:
        return f"{round(days * 24, 1)} hours"
    return f"{days} days"


def current_time() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
