"""Tiny local HTTP server for interactive KG resolution slider.

Serves ``workdir/kg/`` and ``GET /api/graph?resolution=…`` which re-runs Louvain
+ KG assembly (milliseconds at demo scale) and returns vis-network JSON.
"""

from __future__ import annotations

import json
import mimetypes
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def rebuild_graph_payload(
    workdir: Path,
    *,
    resolution: float,
    min_paper_count: int = 2,
    max_terms: int = 40,
    max_island: int = 20,
    document_limit: Optional[int] = None,
    kg_links: Tuple[str, ...] = ("clusters",),
) -> Dict[str, Any]:
    """Re-run Louvain at ``resolution`` and assemble display KG payload."""
    from semantic_corpus.cluster_review.kg import build_kg, nodes_edges_to_vis
    from semantic_corpus.cluster_review.step3 import build_clusters

    if resolution <= 0:
        raise ValueError("resolution must be > 0")

    t0 = time.perf_counter()
    cluster_summary = build_clusters(workdir, resolution=float(resolution))
    t1 = time.perf_counter()
    kg_summary = build_kg(
        workdir,
        kg_links=kg_links,
        max_island=int(max_island),
        min_paper_count=int(min_paper_count),
        max_terms=int(max_terms),
        document_limit=document_limit,
        write_html=True,
        open_browser=False,
        title=f"Knowledge graph ({workdir.name})",
    )
    t2 = time.perf_counter()

    graph_path = Path(kg_summary["graph_path"])
    graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
    vis_nodes, vis_edges = nodes_edges_to_vis(
        graph_doc.get("nodes") or [], graph_doc.get("edges") or []
    )
    counts = kg_summary.get("counts") or {}
    return {
        "ok": True,
        "resolution": float(resolution),
        "nodes": vis_nodes,
        "edges": vis_edges,
        "counts": {
            "nodes": counts.get("nodes"),
            "edges": counts.get("edges"),
            "papers": counts.get("papers"),
            "terms": counts.get("terms"),
            "islands": counts.get("islands"),
            "clusters": cluster_summary.get("cluster_count"),
            "communities": cluster_summary.get("community_count"),
        },
        "timing_ms": {
            "clusters": round((t1 - t0) * 1000, 1),
            "kg": round((t2 - t1) * 1000, 1),
            "total": round((t2 - t0) * 1000, 1),
        },
    }


def _make_handler(
    workdir: Path,
    *,
    min_paper_count: int,
    max_terms: int,
    max_island: int,
    document_limit: Optional[int],
):
    root = (Path(workdir) / "kg").resolve()
    workdir = Path(workdir).resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            print(f"[kg-server] {self.address_string()} {fmt % args}")

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(code, raw, "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path or "/"
            qs = urllib.parse.parse_qs(parsed.query)

            if path in ("/api/graph", "/api/graph/"):
                try:
                    res_raw = (qs.get("resolution") or ["1.0"])[0]
                    resolution = float(res_raw)
                    payload = rebuild_graph_payload(
                        workdir,
                        resolution=resolution,
                        min_paper_count=min_paper_count,
                        max_terms=max_terms,
                        max_island=max_island,
                        document_limit=document_limit,
                    )
                    self._send_json(200, payload)
                except Exception as exc:  # noqa: BLE001 — surface to UI
                    self._send_json(400, {"ok": False, "error": str(exc)})
                return

            if path in ("/", "/index.html", "/knowledge_graph.html"):
                target = root / "knowledge_graph.html"
                if not target.is_file():
                    self._send_json(
                        404,
                        {
                            "ok": False,
                            "error": f"missing {target}; run clusters/encyclopedia with --kg first",
                        },
                    )
                    return
                body = target.read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
                return

            # Static files under kg/ only
            rel = path.lstrip("/")
            if ".." in rel or rel.startswith("/"):
                self._send_json(400, {"ok": False, "error": "bad path"})
                return
            target = (root / rel).resolve()
            if root not in target.parents and target != root:
                self._send_json(403, {"ok": False, "error": "forbidden"})
                return
            if not target.is_file():
                self._send_json(404, {"ok": False, "error": "not found"})
                return
            ctype, _ = mimetypes.guess_type(str(target))
            self._send(200, target.read_bytes(), ctype or "application/octet-stream")

    return Handler


def _bind_server(
    host: str, port: int, handler, *, tries: int = 20
) -> Tuple[ThreadingHTTPServer, int]:
    """Bind ``host:port``, or the next free ports if busy."""
    last_err: Optional[OSError] = None
    for offset in range(max(1, int(tries))):
        candidate = int(port) + offset
        try:
            server = ThreadingHTTPServer((host, candidate), handler)
            server.allow_reuse_address = True
            return server, candidate
        except OSError as exc:
            last_err = exc
            # 48 = EADDRINUSE on macOS; errno may also be in args
            if getattr(exc, "errno", None) not in {48, 98}:
                raise
            continue
    raise OSError(
        f"Could not bind {host}:{port}–{int(port) + tries - 1}: {last_err}. "
        "Stop the other server or pass --port <free>"
    ) from last_err


def serve_kg(
    workdir: Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    min_paper_count: int = 2,
    max_terms: int = 40,
    max_island: int = 20,
    document_limit: Optional[int] = None,
    block: bool = True,
) -> ThreadingHTTPServer:
    """Start the KG viewer server. Blocks if ``block`` is True."""
    workdir = Path(workdir)
    html = workdir / "kg" / "knowledge_graph.html"
    if not html.is_file():
        # Ensure an initial graph exists
        rebuild_graph_payload(
            workdir,
            resolution=1.0,
            min_paper_count=min_paper_count,
            max_terms=max_terms,
            max_island=max_island,
            document_limit=document_limit,
        )

    handler = _make_handler(
        workdir,
        min_paper_count=min_paper_count,
        max_terms=max_terms,
        max_island=max_island,
        document_limit=document_limit,
    )
    server, bound_port = _bind_server(host, int(port), handler)
    if bound_port != int(port):
        print(
            f"[kg-server] port {port} busy — using {bound_port} instead "
            f"(or free it: lsof -nP -iTCP:{port} -sTCP:LISTEN)"
        )
    url = f"http://{host}:{bound_port}/knowledge_graph.html"
    print(f"[kg-view] interactive viewer at {url}")
    print("[kg-view] resolution slider → GET /api/graph?resolution=… (Louvain + KG rebuild)")
    if open_browser:
        webbrowser.open(url)
    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[kg-server] stopped")
            server.shutdown()
    else:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    return server
