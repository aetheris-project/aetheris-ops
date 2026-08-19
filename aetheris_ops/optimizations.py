"""
Optimization rules engine.

Each rule inspects the flat metrics dict produced by `collectors.collect()`
and, when its condition matches, yields a finding with a severity, a clear
explanation and an actionable fix. Rules are pure functions of the metrics
so they can be unit tested and extended without touching the collectors.

Severities: "info" (nice to know), "warning" (recommended), "critical"
(should be fixed). Findings carry a stable `id` used by the report and by
the GitHub issue automation for deduplication.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple


class Finding:
    def __init__(
        self,
        finding_id: str,
        severity: str,
        title: str,
        detail: str,
        fix: Optional[str] = None,
    ):
        self.id = finding_id
        self.severity = severity
        self.title = title
        self.detail = detail
        self.fix = fix

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "fix": self.fix,
        }


Rule = Callable[[Dict], Optional[Finding]]


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    detail: str,
    fix: Optional[str] = None,
) -> Finding:
    return Finding(finding_id, severity, title, detail, fix)


def rule_swappiness(metrics: Dict) -> Optional[Finding]:
    value = metrics.get("vm_swappiness")
    if value is None:
        return None
    if value > 60:
        return _finding(
            "vm-swappiness",
            "warning",
            "High swappiness",
            f"vm.swappiness is {value}; the kernel prefers swapping over page cache.",
            "sysctl -w vm.swappiness=10",
        )
    if value > 30:
        return _finding(
            "vm-swappiness",
            "info",
            "Swappiness above recommended range",
            f"vm.swappiness is {value}. Values 10-30 are typical for database and web workloads.",
            "sysctl -w vm.swappiness=10",
        )
    return None


def rule_memory(metrics: Dict) -> Optional[Finding]:
    percent = metrics.get("mem_available_percent")
    if percent is None:
        return None
    if percent < 10:
        return _finding(
            "mem-pressure",
            "critical",
            "Low available memory",
            f"Only {percent}% of RAM is available; the host is at risk of OOM stalls.",
            "Review running workloads, add RAM or move services to another node.",
        )
    if percent < 20:
        return _finding(
            "mem-pressure",
            "warning",
            "Available memory is low",
            f"Only {percent}% of RAM is available.",
            "Review running workloads or add RAM.",
        )
    return None


def rule_swap_usage(metrics: Dict) -> Optional[Finding]:
    total = metrics.get("swap_total_mb")
    free = metrics.get("swap_free_mb")
    if total is None or free is None or total <= 0:
        return None
    used_percent = round((total - free) / total * 100)
    if used_percent > 80:
        return _finding(
            "swap-pressure",
            "warning",
            "Swap is heavily used",
            f"{used_percent}% of swap is consumed, which degrades latency for hosted services.",
            "Investigate memory pressure and consider raising RAM or reducing swappiness.",
        )
    return None


def rule_disk(metrics: Dict) -> Optional[Finding]:
    percent = metrics.get("disk_used_percent")
    if percent is None:
        return None
    if percent > 92:
        return _finding(
            "disk-full",
            "critical",
            "Root filesystem nearly full",
            f"Root filesystem is at {percent}% capacity.",
            "Free space: prune logs, images and backups.",
        )
    if percent > 80:
        return _finding(
            "disk-full",
            "warning",
            "Root filesystem filling up",
            f"Root filesystem is at {percent}% capacity.",
            "Plan cleanup: prune logs, images and backups.",
        )
    return None


def rule_thp(metrics: Dict) -> Optional[Finding]:
    mode = metrics.get("thp_mode")
    if mode == "always":
        return _finding(
            "thp",
            "warning",
            "Transparent Huge Pages set to always",
            "THP in 'always' mode can cause latency spikes on database and virtualized workloads.",
            "echo madvise > /sys/kernel/mm/transparent_hugepage/enabled",
        )
    return None


def rule_tcp_congestion(metrics: Dict) -> Optional[Finding]:
    cc = metrics.get("tcp_congestion_control")
    if cc is None:
        return None
    if cc not in ("bbr", "cubic"):
        return _finding(
            "tcp-cc",
            "info",
            "Non-default TCP congestion control",
            f"Current congestion control is '{cc}'.",
            "Consider BBR for high-latency links: sysctl -w net.ipv4.tcp_congestion_control=bbr",
        )
    return None


def rule_ip_forward(metrics: Dict) -> Optional[Finding]:
    value = metrics.get("ip_forward")
    if value == 1:
        return _finding(
            "ip-forward",
            "info",
            "IPv4 forwarding is enabled",
            "ip_forward=1 exposes the host as a router; only keep it on if network features need it.",
            "sysctl -w net.ipv4.ip_forward=0 (if not needed)",
        )
    return None


def rule_dirty_ratio(metrics: Dict) -> Optional[Finding]:
    value = metrics.get("vm_dirty_ratio")
    if value is not None and value > 30:
        return _finding(
            "vm-dirty-ratio",
            "info",
            "High dirty page ratio",
            f"vm.dirty_ratio is {value}%; write-heavy workloads may stall.",
            "sysctl -w vm.dirty_ratio=20",
        )
    return None


def rule_load(metrics: Dict) -> Optional[Finding]:
    load5 = metrics.get("load5")
    cores = metrics.get("cores")
    if load5 is None or cores is None or cores == 0:
        return None
    ratio = load5 / cores
    if ratio > 2:
        return _finding(
            "load",
            "warning",
            "Sustained load above CPU capacity",
            f"5-minute load is {load5} on {cores} cores ({round(ratio, 2)}x).",
            "Inspect top services; the host may need more vCPUs or a workload rebalance.",
        )
    if ratio > 1:
        return _finding(
            "load",
            "info",
            "Load approaching CPU capacity",
            f"5-minute load is {load5} on {cores} cores.",
            "Monitor; consider a workload rebalance if sustained.",
        )
    return None


def rule_governor(metrics: Dict) -> Optional[Finding]:
    governor = metrics.get("cpu_governor")
    if governor and governor not in ("performance", "schedutil"):
        return _finding(
            "cpu-governor",
            "info",
            f"CPU governor is '{governor}'",
            "For latency-sensitive hosts, performance or schedutil is recommended.",
            "cpupower frequency-set -g performance (if supported)",
        )
    return None


def rule_journald(metrics: Dict) -> Optional[Finding]:
    value = metrics.get("journald_system_max_use")
    if value is None:
        return None
    if value.strip().lower() == "0":
        return _finding(
            "journald-size",
            "warning",
            "System journal is unbounded",
            "SystemMaxUse=0 disables the journal size cap; logs can fill the disk.",
            "Set SystemMaxUse=500M in /etc/systemd/journald.conf and restart systemd-journald.",
        )
    return None


RULES: List[Rule] = [
    rule_swappiness,
    rule_memory,
    rule_swap_usage,
    rule_disk,
    rule_thp,
    rule_tcp_congestion,
    rule_ip_forward,
    rule_dirty_ratio,
    rule_load,
    rule_governor,
    rule_journald,
]


def evaluate(metrics: Dict, rules: List[Rule] = RULES) -> Tuple[List[Finding], int]:
    """Run all rules and return (findings, host_score).

    Score starts at 100 and subtracts weight per finding: info=0,
    warning=10, critical=25.
    """
    findings: List[Finding] = []
    for rule in rules:
        try:
            finding = rule(metrics)
        except Exception:  # a broken rule must never crash the scan
            continue
        if finding is not None:
            findings.append(finding)

    severity_order = {"info": 0, "warning": 1, "critical": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 0), f.id))

    weight = {"info": 0, "warning": 10, "critical": 25}
    score = max(0, 100 - sum(weight.get(f.severity, 0) for f in findings))
    return findings, score


def grade(score: int) -> str:
    if score >= 95:
        return "A"
    if score >= 85:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"
