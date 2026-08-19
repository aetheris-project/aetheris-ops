"""
Package update detection.

Detects pending OS/package updates through the native package manager
where available: apt on Debian/Ubuntu, Homebrew on macOS, winget on
Windows. Each detector returns a list of `PendingUpdate` records and
never raises - failures degrade to an empty result.

Detectors are pure functions that receive a command runner so they can
be unit tested with canned output.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Optional

Runner = Callable[[List[str]], Optional[str]]


@dataclass
class PendingUpdate:
    package: str
    current: str
    available: str
    manager: str

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "current": self.current,
            "available": self.available,
            "manager": self.manager,
        }


def real_runner(command: List[str]) -> Optional[str]:
    """Run a command, returning its stdout on success or None."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            return None
        return completed.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def _which(binary: str) -> bool:
    return shutil.which(binary) is not None


def parse_apt_output(output: Optional[str]) -> List[PendingUpdate]:
    """Parse `apt list --upgradable` output (Debian/Ubuntu).

    Real output rows look like `nginx/stable 1.26.2-1 amd64 [upgradable
    from: 1.25.4-1]`; the parser tolerates rows without the `/suite` part.
    """
    updates: List[PendingUpdate] = []
    if not output:
        return updates
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Listing"):
            continue
        current_match = re.search(r"upgradable from:\s*([^]]+)", stripped)
        current = current_match.group(1).strip() if current_match else "unknown"
        head = stripped.split("[", 1)[0].split()
        if len(head) >= 3:
            package = head[0].split("/", 1)[0]
            version = head[1]
        elif len(head) == 2:
            package = head[0].split("/", 1)[0]
            version = head[1]
        else:
            continue
        updates.append(PendingUpdate(package, current, version, "apt"))
    return updates


def parse_brew_output(output: Optional[str]) -> List[PendingUpdate]:
    """Parse `brew outdated` output (macOS)."""
    updates: List[PendingUpdate] = []
    if not output:
        return updates
    for line in output.splitlines():
        # Format: package (1.0.0 < 1.2.0)
        match = re.match(r"^(\S+)\s+\(([^<]+)<\s*([^)]+)\)", line)
        if match:
            package, current, available = (part.strip() for part in match.groups())
            updates.append(PendingUpdate(package, current, available, "brew"))
            continue
        # Fallback: just the package name. Skip banner lines like
        # "==> Outdated Formulae" printed by some brew versions.
        name = line.strip()
        if name and not name.startswith("==>"):
            updates.append(PendingUpdate(name, "unknown", "unknown", "brew"))
    return updates


def parse_winget_output(output: Optional[str]) -> List[PendingUpdate]:
    """Parse `winget upgrade` output (Windows), best effort."""
    updates: List[PendingUpdate] = []
    if not output:
        return updates
    for line in output.splitlines():
        # winget table rows look like: Name Id Version Available Source
        parts = line.split()
        if len(parts) >= 4 and parts[0].lower() not in ("name", "---"):
            updates.append(PendingUpdate(parts[0], parts[2], parts[3], "winget"))
    return updates


def detect_apt(runner: Runner = real_runner) -> List[PendingUpdate]:
    if not _which("apt"):
        return []
    output = runner(["apt", "list", "--upgradable"])
    return parse_apt_output(output)


def detect_brew(runner: Runner = real_runner) -> List[PendingUpdate]:
    if not _which("brew"):
        return []
    # Without --quiet brew prints "package (current < available)" rows,
    # which the parser needs to extract real versions.
    output = runner(["brew", "outdated"])
    return parse_brew_output(output)


def detect_winget(runner: Runner = real_runner) -> List[PendingUpdate]:
    if not _which("winget"):
        return []
    output = runner(["winget", "upgrade"])
    return parse_winget_output(output)


def detect_all(runner: Runner = real_runner) -> List[PendingUpdate]:
    """Detect pending updates across all available package managers."""
    updates: List[PendingUpdate] = []
    for detector in (detect_apt, detect_brew, detect_winget):
        try:
            updates.extend(detector(runner))
        except Exception:  # a broken detector must never crash the scan
            continue
    # De-duplicate by package+manager keeping the highest available.
    seen: dict = {}
    for update in updates:
        key = f"{update.manager}:{update.package}"
        if key not in seen or update.available > seen[key].available:
            seen[key] = update
    return list(seen.values())
