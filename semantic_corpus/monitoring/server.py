"""Tiny HTTP server for the live dashboard: one HTML page plus a JSON endpoint."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from semantic_corpus.monitoring.checker import Monitor

DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


class MonitorServer:
    """Serve ``/`` (dashboard) and ``/api/status`` (latest results, no live checks)."""

    def __init__(self, monitor: Monitor, host: str = "127.0.0.1", port: int = 8766):
        self.monitor = monitor
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None

    def _make_handler(self) -> type:
        monitor = self.monitor

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                path = self.path.split("?", 1)[0]
                if path in ("/", "/health.html", "/index.html"):
                    self._send(
                        200, DASHBOARD_PATH.read_bytes(), "text/html; charset=utf-8"
                    )
                elif path == "/api/status":
                    monitor.touch()
                    body = json.dumps(monitor.snapshot()).encode("utf-8")
                    self._send(200, body, "application/json")
                else:
                    self._send(404, b"not found", "text/plain")

            def _send(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass  # the dashboard polls every few seconds; keep the console quiet

        return Handler

    def serve_forever(self) -> None:
        self._server = ThreadingHTTPServer((self.host, self.port), self._make_handler())
        self.monitor.start()
        self._server.serve_forever()

    def shutdown(self) -> None:
        self.monitor.stop()
        if self._server:
            self._server.shutdown()
            self._server.server_close()
