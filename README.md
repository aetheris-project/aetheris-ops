<p align="center">
  <img src="assets/icon.svg" alt="Aetheris Ops" width="88">
</p>

<h1 align="center">Aetheris Ops</h1>

<p align="center">
  <strong>System optimization scanner and update manager for Aetheris hosts</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Linux-macOS-Windows-2ea44f" alt="Linux / macOS / Windows">
  <img src="https://img.shields.io/badge/stdlib-only-18181B" alt="stdlib only">
  <img src="https://img.shields.io/badge/tests-passing-success" alt="Tests passing">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Faetheris-project%2Faetheris-ops%2Fmain%2Freports%2Fbadge.json" alt="Host score">
</p>

---

A pure standard-library Python tool that scans the machine running the
Aetheris platform, detects optimization opportunities across the kernel,
memory, disk, CPU and services, tracks pending package updates, and
publishes everything to GitHub - as a live report, a status badge and
auto-opened issues for critical findings.

No third-party dependencies, no root required for scanning, and it never
applies changes by itself: it tells you what to do and why.

## Features

- **Health score**: a single 0-100 score with an A-F grade, computed from
  weighted optimization findings.
- **Optimization rules**: swappiness, memory pressure, swap usage, disk
  fill, transparent huge pages, TCP congestion control, IPv4 forwarding,
  dirty pages, load vs. cores, CPU governor and unbounded journald.
- **Update management**: detects pending updates through the native package
  manager - `apt` on Debian/Ubuntu, Homebrew on macOS, `winget` on Windows.
- **GitHub vision**: scheduled GitHub Actions run the scan, refresh a
  shields.io endpoint badge, post the report to the workflow summary and
  open (deduplicated) issues labeled `ops:*` for every critical finding.
- **Cross-platform and safe**: every collector degrades to `None` instead of
  raising, scanning needs no privileges, and the tool only reads - it never
  writes system state.

## Installation

The tool has no third-party runtime dependencies - only Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

## Usage

Quick health summary:

```bash
aetheris-ops check
```

Full report written to files:

```bash
aetheris-ops report --out-md reports/latest.md --out-json reports/latest.json
```

Print the report to stdout (markdown or JSON):

```bash
aetheris-ops report --markdown
aetheris-ops report --json
```

List pending package updates:

```bash
aetheris-ops updates
```

Skip update detection in restricted environments:

```bash
aetheris-ops check --no-updates
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Host is clean (no warnings, no criticals, no pending updates) |
| `1` | Warnings detected and/or pending updates |
| `2` | Critical findings detected |

## GitHub automation

The repository ships a scheduled workflow (`.github/workflows/ops-report.yml`)
that runs daily at 04:17 UTC and on every push touching the scanner. Each
run:

1. Installs the package and generates `reports/latest.md` and
   `reports/latest.json` on the runner.
2. Commits any changes back to `main`, keeping the report and the
   `reports/badge.json` shield endpoint fresh.
3. Appends the markdown report to the Actions job summary.
4. Opens a GitHub issue for every critical finding, labeled `ops:<rule-id>`
   - existing open issues for the same rule are never duplicated.

The badge at the top of this README renders the last reported score from
the committed `reports/badge.json`.

To run the same scan on the actual production host and publish it, run:

```bash
aetheris-ops report --out-md reports/latest.md --out-json reports/latest.json
git add reports/ && git commit -m "chore: refresh ops report" && git push
```

## Rules reference

| Rule id | Severity trigger | Suggested fix |
| --- | --- | --- |
| `vm-swappiness` | `> 30` info, `> 60` warning | `sysctl -w vm.swappiness=10` |
| `mem-pressure` | `< 20%` warning, `< 10%` critical | review workloads / add RAM |
| `swap-pressure` | `> 80%` swap used | review memory pressure |
| `disk-full` | `> 80%` warning, `> 92%` critical | prune logs, images, backups |
| `thp` | THP `always` | `echo madvise > /sys/kernel/mm/transparent_hugepage/enabled` |
| `tcp-cc` | non-default congestion control | consider BBR |
| `ip-forward` | `ip_forward=1` (info) | disable if not needed |
| `vm-dirty-ratio` | `> 30` (info) | `sysctl -w vm.dirty_ratio=20` |
| `load` | load/cores `> 1` info, `> 2` warning | rebalance workloads |
| `cpu-governor` | non-performance governor (info) | `cpupower frequency-set -g performance` |
| `journald-size` | `SystemMaxUse=0` | set `SystemMaxUse=500M` |

## Repository layout

```text
aetheris-ops/
├── aetheris_ops/
│   ├── cli.py            # argparse entry point
│   ├── collectors.py     # system metrics (stdlib only)
│   ├── optimizations.py  # rules engine + scoring
│   ├── updates.py        # apt / brew / winget detection
│   └── report.py         # markdown + JSON (shields endpoint) renderers
├── .github/workflows/
│   └── ops-report.yml    # scheduled scan, badge, issues
├── reports/              # generated report + badge (committed)
├── tests/                # unit tests
└── pyproject.toml
```

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

## License

Aetheris is licensed under the [Aetheris License v1.0](LICENSE): source-available, non-commercial, with attribution required. You may use, study, modify and share it for your own purposes, but the core, the Aetheris name and the author's credit may not be removed, and the software may not be sold without written permission.
