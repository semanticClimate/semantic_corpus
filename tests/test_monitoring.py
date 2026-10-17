"""Tests for the repository monitoring dashboard (no network)."""

import json
import threading
import time
from pathlib import Path
from urllib.request import urlopen

from semantic_corpus.monitoring.checker import (
    CheckResult,
    Monitor,
    Target,
    build_targets,
)
from semantic_corpus.monitoring.server import MonitorServer


def _fake_ping(statuses):
    def ping(target, session):
        return CheckResult(
            target.name,
            target.url,
            statuses[target.name],
            200,
            100,
            None,
            None,
            "2026-10-17T00:00:00+00:00",
        )

    return ping


class TestBuildTargets:
    def test_deduplicates_aliases_and_splits_uba(self) -> None:
        names = [t.name for t in build_targets()]
        assert "unam" not in names and "unam_mexico" in names
        assert "unal" not in names and "unal_colombia" in names
        assert {"uba:exactas", "uba:fauba"} <= set(names)
        assert len(names) == len(set(names))


class TestMonitor:
    def test_backoff_on_failure_and_reset_on_success(self) -> None:
        statuses = {"a": "down"}
        monitor = Monitor(
            [Target("a", "http://a")], interval_s=100, ping_fn=_fake_ping(statuses)
        )
        monitor.run_once(force=True)
        first = monitor._next_check["a"] - time.time()
        monitor.run_once(force=True)
        second = monitor._next_check["a"] - time.time()
        assert 150 < first <= 200 and 350 < second <= 400

        statuses["a"] = "up"
        monitor.run_once(force=True)
        assert monitor._next_check["a"] - time.time() <= 100
        monitor.stop()

    def test_deep_check_marks_degraded_when_search_empty(self) -> None:
        monitor = Monitor(
            [Target("a", "http://a", repository_class=object)],  # type: ignore[arg-type]
            deep_interval_s=10,
            ping_fn=_fake_ping({"a": "up"}),
            search_fn=lambda target: [],
        )
        (result,) = monitor.run_once(force=True)
        assert result.status == "degraded" and result.search_ok is False
        monitor.stop()

    def test_idle_pauses_and_touch_resumes(self) -> None:
        monitor = Monitor([Target("a", "http://a")], idle_timeout_s=0)
        time.sleep(0.01)
        assert monitor.is_idle()
        monitor.idle_timeout_s = 60
        monitor.touch()
        assert not monitor.is_idle()
        monitor.stop()

    def test_history_persists_between_runs(self, tmp_path: Path) -> None:
        history = tmp_path / "h.jsonl"
        targets = [Target("a", "http://a")]
        monitor = Monitor(
            targets, history_path=history, ping_fn=_fake_ping({"a": "up"})
        )
        monitor.run_once(force=True)
        monitor.stop()

        reloaded = Monitor(targets, history_path=history)
        snap = reloaded.snapshot()
        assert snap["repositories"][0]["uptime_pct"] == 100
        reloaded.stop()


class TestMonitorServer:
    def test_status_endpoint_and_dashboard(self) -> None:
        monitor = Monitor(
            [Target("a", "http://a")], ping_fn=_fake_ping({"a": "up"}), interval_s=3600
        )
        server = MonitorServer(monitor, port=18772)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.5)
        try:
            data = json.loads(urlopen("http://127.0.0.1:18772/api/status").read())
            assert data["repositories"][0]["latest"]["status"] == "up"
            page = urlopen("http://127.0.0.1:18772/").read()
            assert b"/api/status" in page
        finally:
            server.shutdown()
