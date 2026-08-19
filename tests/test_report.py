"""Unit tests for report rendering."""

from aetheris_ops.optimizations import Finding
from aetheris_ops.report import render_json, render_markdown
from aetheris_ops.updates import PendingUpdate


def _sample_data():
    metrics = {
        "hostname": "test-host",
        "platform": "Linux",
        "release": "6.8.0",
        "arch": "x86_64",
        "python_version": "3.12.0",
        "uptime_days": 3.5,
        "cores": 8,
    }
    findings = [
        Finding("vm-swappiness", "warning", "High swappiness", "vm.swappiness is 90", "sysctl -w vm.swappiness=10")
    ]
    updates = [PendingUpdate("nginx", "1.25.4-1", "1.26.2-1", "apt")]
    return metrics, findings, updates


def test_markdown_contains_sections():
    metrics, findings, updates = _sample_data()
    markdown = render_markdown(metrics, findings, updates, score=90)
    assert "# Aetheris host report" in markdown
    assert "## Host" in markdown
    assert "## Score" in markdown
    assert "## Optimizations" in markdown
    assert "## Pending updates" in markdown
    assert "test-host" in markdown
    assert "sysctl -w vm.swappiness=10" in markdown
    assert "nginx" in markdown


def test_json_is_shield_endpoint_compatible():
    metrics, findings, updates = _sample_data()
    payload = render_json(metrics, findings, updates, score=90)
    assert payload["schemaVersion"] == 1
    assert payload["label"] == "host score"
    assert payload["message"] == "90/100"
    assert payload["color"] == "success"
    assert payload["report"]["score"] == 90
    assert payload["report"]["grade"] == "B"
    assert len(payload["report"]["optimizations"]) == 1
    assert len(payload["report"]["pending_updates"]) == 1
