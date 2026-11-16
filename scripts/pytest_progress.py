#!/usr/bin/env python3
"""Run pytest printing one START/PASS/FAIL line per test (find hangs).

Usage:
  ./venv/bin/python scripts/pytest_progress.py
  ./venv/bin/python scripts/pytest_progress.py tests/test_coding_style.py -x
"""

from __future__ import annotations

import sys

import pytest


class ProgressPlugin:
    """Flush a one-line status as each test starts and finishes."""

    def pytest_runtest_logstart(self, nodeid, location):
        print(f"START {nodeid}", flush=True)

    def pytest_runtest_logreport(self, report):
        if report.when == "setup" and report.failed:
            print(f"FAIL  {report.nodeid} (setup)", flush=True)
            return
        if report.when != "call":
            return
        if report.passed:
            print(f"PASS  {report.nodeid}", flush=True)
        elif report.failed:
            print(f"FAIL  {report.nodeid}", flush=True)
        elif report.skipped:
            print(f"SKIP  {report.nodeid}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        args = ["tests/", "-q", "--tb=line"]
    # Avoid double progress bars fighting START lines
    if "-v" not in args and "--verbose" not in args:
        args = ["-q", *args] if args[0] != "-q" else args
    return pytest.main(args, plugins=[ProgressPlugin()])


if __name__ == "__main__":
    raise SystemExit(main())
