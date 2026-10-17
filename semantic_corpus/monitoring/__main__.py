"""Entry point: ``python -m semantic_corpus.monitoring {serve,check}``."""

import argparse
import json
import sys
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from semantic_corpus.monitoring.checker import Monitor, build_targets
from semantic_corpus.monitoring.server import MonitorServer

ICONS = {"up": "🟢", "slow": "🟡", "warn": "🟠", "degraded": "🟠", "down": "🔴"}


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_corpus.monitoring",
        description="Monitor whether the configured repositories are responding.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Start the live dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    serve.add_argument(
        "--interval", type=int, default=300, help="Seconds between pings"
    )
    serve.add_argument(
        "--deep",
        action="store_true",
        help="Also run a one-result search per repository (every --deep-interval)",
    )
    serve.add_argument("--deep-interval", type=int, default=3600)
    serve.add_argument(
        "--idle-timeout",
        type=int,
        default=600,
        help="Pause checks after this many seconds without the dashboard open",
    )
    serve.add_argument(
        "--history", type=Path, default=Path("temp/monitoring/health_history.jsonl")
    )
    serve.add_argument("--no-browser", action="store_true")

    check = sub.add_parser("check", help="Check once and print a table")
    check.add_argument("--deep", action="store_true")
    check.add_argument("--json", action="store_true", help="Print JSON instead")
    return parser.parse_args(argv)


def _check(args: argparse.Namespace) -> int:
    monitor = Monitor(build_targets(), deep_interval_s=1 if args.deep else None)
    results = monitor.run_once(force=True)
    monitor.stop()
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            latency = f"{r.latency_ms} ms" if r.latency_ms is not None else "-"
            code = r.http_code if r.http_code is not None else "-"
            search = {True: "search ok", False: "search FAIL", None: ""}[r.search_ok]
            print(
                f"{ICONS[r.status]} {r.name:16} {r.status:9} {code!s:4} {latency:>8}  {search}"
            )
            if r.error:
                print(f"   └ {r.error}")
    return 0 if all(r.status not in ("down", "degraded") for r in results) else 1


def _serve(args: argparse.Namespace) -> int:
    monitor = Monitor(
        build_targets(),
        interval_s=args.interval,
        deep_interval_s=args.deep_interval if args.deep else None,
        idle_timeout_s=args.idle_timeout,
        history_path=args.history,
    )
    server = MonitorServer(monitor, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/"
    print(f"Repository monitor: {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping monitor.")
    finally:
        server.shutdown()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # emoji icons on Windows consoles
    return _serve(args) if args.command == "serve" else _check(args)


if __name__ == "__main__":
    sys.exit(main())
