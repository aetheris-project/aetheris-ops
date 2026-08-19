"""Unit tests for the optimization rules engine."""

from aetheris_ops.optimizations import RULES, evaluate, grade


def test_clean_host_scores_full():
    metrics = {
        "vm_swappiness": 10,
        "mem_available_percent": 55,
        "swap_total_mb": 1024,
        "swap_free_mb": 1024,
        "disk_used_percent": 45,
        "thp_mode": "madvise",
        "tcp_congestion_control": "bbr",
        "ip_forward": 0,
        "vm_dirty_ratio": 20,
        "load5": 1.0,
        "cores": 8,
        "cpu_governor": "performance",
        "journald_system_max_use": "500M",
    }
    findings, score = evaluate(metrics)
    assert score == 100
    assert grade(score) == "A"
    assert findings == []


def test_critical_disk_and_memory():
    metrics = {
        "disk_used_percent": 95,
        "mem_available_percent": 5,
        "vm_swappiness": 60,
    }
    findings, score = evaluate(metrics)
    severities = {f.severity for f in findings}
    assert "critical" in severities
    assert score <= 75


def test_findings_carry_ids_and_fixes():
    metrics = {"vm_swappiness": 90, "disk_used_percent": 85}
    findings, _ = evaluate(metrics)
    by_id = {f.id: f for f in findings}
    assert by_id["vm-swappiness"].fix.startswith("sysctl")
    assert by_id["disk-full"].severity == "warning"


def test_broken_rule_never_crashes():
    def exploding(_metrics):
        raise RuntimeError("boom")

    metrics = {}
    findings, score = evaluate(metrics, rules=[*RULES, exploding])
    assert score == 100
    assert isinstance(findings, list)
