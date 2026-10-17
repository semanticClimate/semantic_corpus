"""Polite health checks for repositories, run periodically in a background thread."""

import json
import logging
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Type

import requests

from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.core.repository_interface import RepositoryInterface

logger = logging.getLogger(__name__)

USER_AGENT = (
    "semantic_corpus-monitor/0.1 (+https://github.com/semanticClimate/semantic_corpus)"
)
REQUEST_TIMEOUT_S = 10
SLOW_THRESHOLD_MS = 3000
DEEP_TIMEOUT_S = 60
DEEP_QUERY = "climate"
MAX_BACKOFF_FACTOR = 8
HISTORY_PER_TARGET = 60

# API roots that only answer with query parameters: ping a minimal real query instead.
PING_URL_OVERRIDES = {
    "europe_pmc": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1",
    "arxiv": "http://export.arxiv.org/api/query?search_query=all:test&max_results=1",
}


@dataclass
class Target:
    """One URL to monitor, linked to the repository class that queries it."""

    name: str
    url: str
    repository_class: Optional[Type[RepositoryInterface]] = None
    search_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    name: str
    url: str
    status: str  # "up" | "slow" | "warn" | "degraded" | "down"
    http_code: Optional[int]
    latency_ms: Optional[int]
    search_ok: Optional[bool]
    error: Optional[str]
    checked_at: str


def build_targets() -> List[Target]:
    """One target per repository class (aliases deduplicated), plus UBA's sub-sources."""
    first_name: Dict[Type[RepositoryInterface], str] = {}
    for name, cls in RepositoryFactory._repositories.items():
        first_name.setdefault(cls, name)

    targets: List[Target] = []
    for cls, name in first_name.items():
        sources = getattr(cls, "SOURCES", None)
        if sources:
            for key, source in sources.items():
                targets.append(
                    Target(f"{name}:{key}", source["base_url"], cls, {"source": key})
                )
            continue
        url = PING_URL_OVERRIDES.get(name) or cls().base_url
        targets.append(Target(name, url, cls))
    return targets


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ping(target: Target, session: requests.Session) -> CheckResult:
    """GET only the response headers (stream=True) and classify the answer."""
    start = time.perf_counter()
    try:
        response = session.get(target.url, stream=True, timeout=REQUEST_TIMEOUT_S)
        response.close()
    except requests.RequestException as exc:
        return CheckResult(
            target.name, target.url, "down", None, None, None, _short_error(exc), _now()
        )

    latency = int((time.perf_counter() - start) * 1000)
    code = response.status_code
    if code >= 500:
        status = "down"
    elif code >= 400:
        status = "warn"  # server answers but rejects us (anti-bot, auth, moved page)
    elif latency > SLOW_THRESHOLD_MS:
        status = "slow"
    else:
        status = "up"
    return CheckResult(
        target.name, target.url, status, code, latency, None, None, _now()
    )


def search_once(target: Target) -> List[Dict[str, Any]]:
    """Run a one-result search through the real repository adapter."""
    assert target.repository_class is not None
    repository = target.repository_class()
    return repository.search_papers(DEEP_QUERY, 1, **target.search_kwargs)


def apply_deep_result(result: CheckResult, future: "Future[Any]") -> None:
    """Fold a search outcome into the ping result; mark degraded if it failed."""
    try:
        result.search_ok = bool(future.result(timeout=DEEP_TIMEOUT_S))
    except FutureTimeout:
        result.search_ok, result.error = (
            False,
            f"search timed out after {DEEP_TIMEOUT_S}s",
        )
    except Exception as exc:  # noqa: BLE001 - any adapter failure means degraded
        result.search_ok, result.error = False, _short_error(exc)
    if not result.search_ok:
        result.status = "degraded"
        result.error = result.error or "search returned no results"


def _short_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:200]


class Monitor:
    """Checks targets on a schedule; pauses itself when nobody is looking."""

    def __init__(
        self,
        targets: List[Target],
        *,
        interval_s: int = 300,
        deep_interval_s: Optional[int] = None,
        idle_timeout_s: int = 600,
        history_path: Optional[Path] = None,
        ping_fn: Callable[[Target, requests.Session], CheckResult] = ping,
        search_fn: Callable[[Target], List[Dict[str, Any]]] = search_once,
    ) -> None:
        self.targets = targets
        self.interval_s = interval_s
        self.deep_interval_s = deep_interval_s
        self.idle_timeout_s = idle_timeout_s
        self.history_path = Path(history_path) if history_path else None
        self.ping_fn = ping_fn
        self.search_fn = search_fn

        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.pool = ThreadPoolExecutor(max_workers=6)

        self.latest: Dict[str, CheckResult] = {}
        self.history: Dict[str, Deque[Dict[str, Any]]] = {
            t.name: deque(maxlen=HISTORY_PER_TARGET) for t in targets
        }
        self._failures: Dict[str, int] = {t.name: 0 for t in targets}
        self._next_check: Dict[str, float] = {t.name: 0.0 for t in targets}
        self._next_deep: Dict[str, float] = {t.name: 0.0 for t in targets}
        self._last_viewed = time.time()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._load_history()

    # -- scheduling -------------------------------------------------------

    def touch(self) -> None:
        """Mark that someone is viewing; resumes checks immediately if paused."""
        was_idle = self.is_idle()
        self._last_viewed = time.time()
        if was_idle:
            self._wake.set()

    def is_idle(self) -> bool:
        return time.time() - self._last_viewed > self.idle_timeout_s

    def run_once(self, force: bool = False) -> List[CheckResult]:
        """Check every target that is due (or all of them when ``force``)."""
        now = time.time()
        due = [t for t in self.targets if force or now >= self._next_check[t.name]]
        results = list(self.pool.map(lambda t: self.ping_fn(t, self.session), due))

        searches: Dict[str, "Future[Any]"] = {}
        if self.deep_interval_s:
            for target, result in zip(due, results):
                deep_due = force or now >= self._next_deep[target.name]
                if deep_due and target.repository_class and result.status != "down":
                    searches[target.name] = self.pool.submit(self.search_fn, target)
                    self._next_deep[target.name] = now + self.deep_interval_s

        for target, result in zip(due, results):
            if target.name in searches:
                apply_deep_result(result, searches[target.name])
            self._record(target, result, now)
        return results

    def _record(self, target: Target, result: CheckResult, now: float) -> None:
        failed = result.status in ("down", "degraded")
        self._failures[target.name] = self._failures[target.name] + 1 if failed else 0
        backoff = (
            min(2 ** self._failures[target.name], MAX_BACKOFF_FACTOR) if failed else 1
        )
        self._next_check[target.name] = now + self.interval_s * backoff

        with self._lock:
            self.latest[target.name] = result
            self.history[target.name].append(
                {"t": result.checked_at, "s": result.status, "ms": result.latency_ms}
            )
        self._append_history(result)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self.pool.shutdown(wait=False)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self.is_idle():
                try:
                    self.run_once()
                except Exception:  # noqa: BLE001 - keep the monitor alive
                    logger.exception("health check cycle failed")
            # wake up at the next due check, or when a viewer returns
            sleep_for = max(1.0, min(self._next_check.values()) - time.time())
            self._wake.wait(timeout=sleep_for)
            self._wake.clear()

    # -- state ------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            repos = []
            for target in self.targets:
                latest = self.latest.get(target.name)
                history = list(self.history[target.name])
                ok = sum(1 for h in history if h["s"] in ("up", "slow", "warn"))
                repos.append(
                    {
                        "name": target.name,
                        "url": target.url,
                        "latest": asdict(latest) if latest else None,
                        "history": history,
                        "uptime_pct": round(100 * ok / len(history))
                        if history
                        else None,
                    }
                )
        return {
            "generated_at": _now(),
            "interval_s": self.interval_s,
            "deep_interval_s": self.deep_interval_s,
            "paused": self.is_idle(),
            "repositories": repos,
        }

    def _append_history(self, result: CheckResult) -> None:
        if not self.history_path:
            return
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(result)) + "\n")

    def _load_history(self) -> None:
        if not self.history_path or not self.history_path.is_file():
            return
        with self.history_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("name") in self.history:
                    self.history[row["name"]].append(
                        {
                            "t": row["checked_at"],
                            "s": row["status"],
                            "ms": row["latency_ms"],
                        }
                    )
