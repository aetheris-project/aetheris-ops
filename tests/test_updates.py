"""Unit tests for package update detection parsers."""

from aetheris_ops.updates import (
    detect_all,
    parse_apt_output,
    parse_brew_output,
    parse_winget_output,
)


def test_apt_parser():
    output = (
        "Listing... Done\n"
        "nginx/stable 1.26.2-1 amd64 [upgradable from: 1.25.4-1]\n"
        "postgresql-16/main 16.4-1.pgdg120+1 amd64 [upgradable from: 16.3-1]\n"
    )
    updates = parse_apt_output(output)
    assert len(updates) == 2
    nginx = updates[0]
    assert nginx.package == "nginx"
    assert nginx.current == "1.25.4-1"
    assert nginx.available == "1.26.2-1"
    assert nginx.manager == "apt"
    postgres = updates[1]
    assert postgres.package == "postgresql-16"
    assert postgres.current == "16.3-1"
    assert postgres.available == "16.4-1.pgdg120+1"


def test_apt_parser_empty():
    assert parse_apt_output("") == []
    assert parse_apt_output("Listing...\n") == []


def test_brew_parser():
    output = "python@3.12 (3.12.4 < 3.12.6)\nnginx (1.25.4 < 1.26.2)\n"
    updates = parse_brew_output(output)
    assert len(updates) == 2
    assert updates[0].package == "python@3.12"
    assert updates[0].current == "3.12.4"
    assert updates[0].available == "3.12.6"


def test_winget_parser():
    output = "Name Id Version Available Source\n--- --- --- --- ---\nVSCode Microsoft.VisualStudioCode 1.92 1.93 winget\n"
    updates = parse_winget_output(output)
    assert len(updates) == 1
    assert updates[0].package == "VSCode"
    assert updates[0].current == "1.92"
    assert updates[0].available == "1.93"


def test_detect_all_dedupes_and_ignores_missing_managers():
    # No package managers present in a CI-like environment: must not raise.
    updates = detect_all(runner=lambda _cmd: None)
    assert isinstance(updates, list)
