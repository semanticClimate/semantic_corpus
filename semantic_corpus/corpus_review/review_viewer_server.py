"""Local HTTP server for HTML review tools."""

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from semantic_corpus.corpus_review.interactive_review import ReviewSession, ReviewSessionConfig
from semantic_corpus.corpus_review.review_table import export_review_tables
from semantic_corpus.corpus_review.text_preview import (
    build_paper_preview,
    resolve_document_paths,
    render_jats_to_html,
)

_PAPER_FILENAME = re.compile(r"^[A-Za-z0-9._-]+\.(pdf|html)$")


def infer_corpus_dir(query_dir: Optional[Path]) -> Optional[Path]:
    """Guess BAGIT corpus directory from query folder name (e.g. corpora/climate_anxiety_2026)."""
    if not query_dir:
        return None
    query_dir = Path(query_dir).resolve()
    name = query_dir.name
    for parent in query_dir.parents:
        candidate = parent / "corpora" / name
        if candidate.is_dir() and (
            (candidate / "data").is_dir() or (candidate / "bagit.txt").is_file()
        ):
            return candidate.resolve()
    candidate = Path.cwd() / "corpora" / name
    if candidate.is_dir() and (
        (candidate / "data").is_dir() or (candidate / "bagit.txt").is_file()
    ):
        return candidate.resolve()
    return None


class ReviewViewerServer:
    """Serve review HTML files, paper documents, and persist review decisions."""

    def __init__(
        self,
        *,
        review_dir: Path,
        review_table_path: Path,
        session_config: Optional[ReviewSessionConfig] = None,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.review_dir = Path(review_dir)
        self.review_table_path = Path(review_table_path)
        self.session_config = session_config
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._session: Optional[ReviewSession] = None

    def _get_session(self) -> ReviewSession:
        if self._session is None:
            config = self.session_config or ReviewSessionConfig(
                review_table_path=self.review_table_path
            )
            self._session = ReviewSession.load(config)
        return self._session

    def _reload_session(self) -> ReviewSession:
        self._session = None
        return self._get_session()

    def _resolve_document(self, filename: str) -> Optional[Path]:
        if not _PAPER_FILENAME.match(filename):
            return None

        stem = Path(filename).stem
        config = self.session_config
        session = self._get_session()

        row: Dict[str, Any] = {"pmcid": stem, "paper_id": f"europe_pmc_{stem}"}
        for candidate in session.rows:
            if candidate.get("pmcid") == stem or candidate.get("paper_id") == stem:
                row = candidate
                break
            if candidate.get("paper_id") == f"europe_pmc_{stem}":
                row = candidate
                break

        paths = resolve_document_paths(
            row,
            query_dir=config.query_dir if config else None,
            xml_dir=config.xml_dir if config else None,
            corpus_dir=config.corpus_dir if config else None,
        )
        ext = Path(filename).suffix.lower().lstrip(".")
        path = paths.get("pdf_path" if ext == "pdf" else "html_path")
        if path and Path(path).is_file():
            return Path(path).resolve()
        return None

    def _make_handler(self):
        review_dir = self.review_dir
        review_table_path = self.review_table_path
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                return

            def _send_json(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_bytes(self, content: bytes, content_type: str, *, status: int = 200, extra_headers: Optional[Dict[str, str]] = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                if extra_headers:
                    for key, value in extra_headers.items():
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(content)

            def _send_file(self, file_path: Path) -> None:
                content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                data = file_path.read_bytes()
                size = len(data)
                range_header = self.headers.get("Range")
                if range_header:
                    match = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
                    if match:
                        start_str, end_str = match.groups()
                        start = int(start_str) if start_str else 0
                        end = int(end_str) if end_str else size - 1
                        end = min(end, size - 1)
                        if start <= end:
                            chunk = data[start : end + 1]
                            self._send_bytes(
                                chunk,
                                content_type,
                                status=206,
                                extra_headers={
                                    "Accept-Ranges": "bytes",
                                    "Content-Range": f"bytes {start}-{end}/{size}",
                                    "Content-Disposition": "inline",
                                },
                            )
                            return
                self._send_bytes(
                    data,
                    content_type,
                    extra_headers={
                        "Accept-Ranges": "bytes",
                        "Content-Disposition": "inline",
                    },
                )

            def _paper_preview(self, query: Dict[str, List[str]]) -> None:
                index_values = query.get("index", [])
                if not index_values:
                    self._send_json(400, {"error": "Missing index"})
                    return
                try:
                    index = int(index_values[0])
                except ValueError:
                    self._send_json(400, {"error": "Invalid index"})
                    return

                session = server._get_session()
                if index < 0 or index >= len(session.rows):
                    self._send_json(404, {"error": "Paper not found"})
                    return

                row = session.rows[index]
                config = server.session_config or ReviewSessionConfig(
                    review_table_path=review_table_path
                )
                preview = build_paper_preview(
                    row,
                    search_metadata=session._lookup_search_metadata(row),
                    query_dir=config.query_dir,
                    xml_dir=config.xml_dir,
                    corpus_dir=config.corpus_dir,
                    intro_max_chars=config.intro_max_chars,
                )
                pmcid = row.get("pmcid") or ""
                paths = resolve_document_paths(
                    row,
                    query_dir=config.query_dir,
                    xml_dir=config.xml_dir,
                    corpus_dir=config.corpus_dir,
                )
                html_url = None
                if paths.get("html_path") and pmcid:
                    html_url = f"/papers/{pmcid}.html"
                elif paths.get("xml_path") and pmcid:
                    html_url = f"/papers/{pmcid}.xml"

                payload: Dict[str, Any] = {
                    "abstract": preview.get("abstract") or row.get("abstract_snippet") or "",
                    "intro": preview.get("intro") or "",
                    "pdf_url": f"/papers/{pmcid}.pdf" if paths.get("pdf_path") and pmcid else None,
                    "html_url": html_url,
                    "formats": {
                        "pdf": bool(paths.get("pdf_path")),
                        "html": bool(paths.get("html_path")),
                        "xml": bool(paths.get("xml_path")),
                    },
                }
                self._send_json(200, payload)

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = unquote(parsed.path)

                if path == "/api/health":
                    self._send_json(200, {"ok": True})
                    return

                if path == "/api/paper-preview":
                    self._paper_preview(parse_qs(parsed.query))
                    return

                if path.startswith("/papers/"):
                    filename = path.split("/papers/", 1)[-1]
                    # Serve rendered HTML for JATS XML files.
                    if filename.lower().endswith(".xml"):
                        stem = Path(filename).stem
                        config = server.session_config
                        session = server._get_session()
                        row: Dict[str, Any] = {"pmcid": stem, "paper_id": f"europe_pmc_{stem}"}
                        for candidate in session.rows:
                            if candidate.get("pmcid") == stem or candidate.get("paper_id") == stem:
                                row = candidate
                                break
                            if candidate.get("paper_id") == f"europe_pmc_{stem}":
                                row = candidate
                                break

                        paths = resolve_document_paths(
                            row,
                            query_dir=config.query_dir if config else None,
                            xml_dir=config.xml_dir if config else None,
                            corpus_dir=config.corpus_dir if config else None,
                        )
                        xml_path = paths.get("xml_path")
                        if not xml_path:
                            self.send_error(404)
                            return
                        rendered = render_jats_to_html(Path(xml_path))
                        if not rendered:
                            self.send_error(500)
                            return
                        self._send_bytes(rendered.encode("utf-8"), "text/html; charset=utf-8")
                        return

                    document = server._resolve_document(filename)
                    if not document:
                        self.send_error(404)
                        return
                    self._send_file(document)
                    return

                if path in {"/", "/index.html"}:
                    index = review_dir / "index.html"
                    if index.is_file():
                        self._send_bytes(index.read_bytes(), "text/html; charset=utf-8")
                        return
                    body = (
                        "<html><body><ul>"
                        '<li><a href="review_table.html">review_table.html</a> — edit all papers in a table</li>'
                        '<li><a href="review_viewer.html">review_viewer.html</a> — one paper at a time</li>'
                        "</ul></body></html>"
                    ).encode("utf-8")
                    self._send_bytes(body, "text/html; charset=utf-8")
                    return

                relative = path.lstrip("/")
                file_path = (review_dir / relative).resolve()
                if not str(file_path).startswith(str(review_dir.resolve())):
                    self.send_error(403)
                    return
                if not file_path.is_file():
                    self.send_error(404)
                    return

                if file_path.suffix == ".css":
                    content_type = "text/css; charset=utf-8"
                elif file_path.suffix == ".html":
                    content_type = "text/html; charset=utf-8"
                else:
                    content_type = "application/octet-stream"
                self._send_bytes(file_path.read_bytes(), content_type)

            def do_POST(self) -> None:
                if urlparse(self.path).path != "/api/save":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    rows = payload["rows"]
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    self._send_json(400, {"error": f"Invalid payload: {exc}"})
                    return

                export_review_tables(rows, review_table_path.parent)
                server._reload_session()
                self._send_json(200, {"saved": str(review_table_path)})

        return Handler

    def serve_forever(self) -> None:
        handler = self._make_handler()
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        print(f"Review tools: http://{self.host}:{self.port}/")
        print(f"  Table (edit): http://{self.host}:{self.port}/review_table.html")
        print(f"  Paper-by-paper: http://{self.host}:{self.port}/review_viewer.html")
        print(f"Saving to: {self.review_table_path.parent}/")
        print("Full papers are served from disk (PDF/HTML) — not copied into HTML.")
        self._server.serve_forever()

    def shutdown(self) -> None:
        if self._server:
            self._server.shutdown()
