<p align="center">
 <img src="assets/icon.svg" alt="Aetheris Ops" width="88" style="filter: drop-shadow(0 0 20px rgba(245,158,11,0.55))">
</p>

<h1 align="center">Aetheris Ops</h1>

<p align="center">
 <strong>Host health scanner, optimization advisor and rolling-update reporter for Aetheris nodes</strong>
</p>

<p align="center">
 <a href="https://aetheris-docs.vercel.app/wiki/monitoring"><img src="https://img.shields.io/badge/Docs-Monitoring-0EA5E9?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Docs"></a>
 <a href="https://github.com/aetheris-project/aetheris-ops/actions/workflows/ops-report.yml"><img src="https://img.shields.io/badge/CI-Daily%20Scan-F59E0B?style=for-the-badge&logo=githubactions&logoColor=white" alt="CI"></a>
 <a href="https://discord.gg/6GcfebuT2A"><img src="https://img.shields.io/badge/Discord-Help-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
 <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
 <img src="https://img.shields.io/badge/Linux-macOS--Windows-2ea44f?style=flat-square" alt="Cross-platform">
 <img src="https://img.shields.io/badge/Stdlib--Only-0%20Deps-18181B?style=flat-square" alt="Zero deps">
 <img src="https://img.shields.io/badge/Read--Only-Safe-10B981?style=flat-square" alt="Safe">
 <img src="https://img.shields.io/badge/Tests-Passing-10B981?style=flat-square" alt="Tests">
 <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Faetheris-project%2Faetheris-ops%2Fmain%2Freports%2Fbadge.json&style=flat-square" alt="Score">
</p>

---

<br>

> **Pure standard-library Python host inspector** that scans the machine running
> the Aetheris control plane, grades it with a single 0-100 health score,
> surfaces kernel / memory / disk / networking optimization opportunities,
> detects pending package updates across distros, and publishes everything
> automatically — a shields.io badge, a Markdown report and deduplicated
> GitHub issues for every critical finding.
>
> **Read-only by design.** Scanning requires no privileges, no third-party
> packages, and the tool never modifies system state.

<br>

## Features

<table>
 <tr>
 <td width="33%" align="center" valign="top">
 <h3> Health score</h3>
 <p>Single 0-100 grade with A-F letter class, weighted across kernel, memory, disk, load and update findings.</p>
 </td>
 <td width="33%" align="center" valign="top">
 <h3> 11+ rules</h3>
 <p>swappiness · THP · TCP BBR · vm.dirty_ratio · load/cores · CPU governor · journald sizing · disk fill · swap pressure</p>
 </td>
 <td width="33%" align="center" valign="top">
 <h3> Update tracker</h3>
 <p>
 apt (Debian/Ubuntu)<br>
 Homebrew (macOS)<br>
 winget (Windows)
 </p>
 </td>
 </tr>
 <tr>
 <td align="center" valign="top">
 <h3> GitHub vision</h3>
 <p>Scheduled Actions refresh the live badge, post the report to job summary and open dedup'd issues labeled <code>ops:*</code>.</p>
 </td>
 <td align="center" valign="top">
 <h3> Read-only</h3>
 <p>Every collector degrades gracefully to <code>None</code>. Scanning never writes, never roots, never raises.</p>
 </td>
 <td align="center" valign="top">
 <h3> Multi-format</h3>
 <p>Human-readable Markdown, machine JSON, shield endpoint compatible with shields.io <code>endpoint</code>.</p>
 </td>
 </tr>
</table>

<br>

## Quick Start

```bash
# 1. Clone (or just grab aetheris_ops/ — no deps required)
git clone https://github.com/aetheris-project/aetheris-ops && cd aetheris-ops

# 2. Optional editable install (adds the `aetheris-ops` CLI)
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\activate
pip install -e .

# 3. One-shot health summary
aetheris-ops check

# 4. Full report (stdout + files + badge JSON)
aetheris-ops report --markdown
aetheris-ops report --out-md reports/latest.md --out-json reports/latest.json

# 5. Pending updates only
aetheris-ops updates

# 6. Skip update check (restricted / offline runners)
aetheris-ops check --no-updates
```

### Exit codes

| Code | Meaning |
|---|---|
| <kbd>0</kbd> | Clean — no warnings, no criticals, no pending updates |
| <kbd>1</kbd> | Warnings and/or pending updates present |
| <kbd>2</kbd> | Critical findings — review immediately |

<br>

## Rules Reference

| Rule ID | Trigger (info / warn / critical) | Suggested fix |
|---|---|---|
| `vm-swappiness` | `> 30` info · `> 60` warn | `sysctl -w vm.swappiness=10` |
| `mem-pressure` | `< 20%` warn · `< 10%` critical | Review workloads / add RAM |
| `swap-pressure` | `> 80%` swap used — warn | Reassess memory sizing |
| `disk-full` | `> 80%` warn · `> 92%` critical | Prune logs, images, backups |
| `thp` | Transparent HugePages `always` | `echo madvise > /sys/kernel/mm/transparent_hugepage/enabled` |
| `tcp-cc` | Non-default congestion control — info | Consider `tcp_bbr` |
| `ip-forward` | `net.ipv4.ip_forward=1` — info | Disable unless routing / KVM |
| `vm-dirty-ratio` | `> 30` info | `sysctl -w vm.dirty_ratio=20` |
| `load` | load/cores `> 1` info · `> 2` warn | Rebalance workloads across nodes |
| `cpu-governor` | Non-performance governor — info | `cpupower frequency-set -g performance` |
| `journald-size` | `SystemMaxUse=0` unbounded — info | Set `SystemMaxUse=500M` in `journald.conf` |

<br>

## GitHub Automation

`.github/workflows/ops-report.yml` runs **daily at 04:17 UTC** and on every push touching the scanner. On each run:

1. The package is installed and `aetheris-ops report` regenerates `reports/latest.md`, `reports/latest.json` and `reports/badge.json`.
2. Changes are committed back to `main` — the top-of-readme score badge always reflects the last run.
3. The Markdown report is appended to the **GitHub Actions job summary**.
4. A deduplicated issue labeled `ops:<rule-id>` is opened per critical finding. Open issues for the same rule are never duplicated.

To publish the scan of a **production host** instead of the runner:

```bash
aetheris-ops report --out-md reports/latest.md --out-json reports/latest.json
git add reports/
git commit -m "chore(ops): refresh production host report"
git push
```

<br>

## Repository Layout

```text
aetheris-ops/
├── aetheris_ops/
│ ├── cli.py # argparse entrypoint (aetheris-ops check|report|updates)
│ ├── collectors.py # sysfs / proc / psutil-free metric collection (stdlib only)
│ ├── optimizations.py # 11-rule engine + weighted A-F scoring
│ ├── updates.py # apt / brew / winget pending-update detectors
│ ├── report.py # Markdown · JSON · shields-endpoint renderers
│ └── __main__.py
├── .github/workflows/
│ └── ops-report.yml # Scheduled daily scan → badge + report + issues
├── reports/ # committed output: latest.md · latest.json · badge.json
├── tests/ # Scoring, ranking, dedup, exit-code tests
└── pyproject.toml
```

<br>

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

Suite covers: scoring math and grade boundaries, rule severity thresholds,
report formatting, exit-code mapping, issue dedup keys.

---

<p align="center">
 <strong>Made with care by <a href="https://github.com/Leo-Galli">Leonardo Galli</a></strong>
</p>

<p align="center">
 <a href="https://github.com/aetheris-project/aetheris-app">App</a>
 ·
 <a href="https://github.com/aetheris-project/aetheris-docs">Docs</a>
 ·
 <a href="https://github.com/aetheris-project/aetheris-installer">Installer</a>
 ·
 <a href="https://discord.gg/6GcfebuT2A">Discord</a>
 ·
 <a href="https://paypal.me/LeonardoGalliITA">Donate</a>
</p>

## License

Licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.
See [LICENSE.md](LICENSE.md). You may use, study, modify and redistribute
for any purpose provided distributed or network-served modified versions
keep this license, preserve Leonardo Galli's copyright notice and release
source under AGPL-3.0. The Aetheris core and author credit may not be removed.
