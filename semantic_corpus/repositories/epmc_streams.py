"""Independent Europe PMC content streams: JSON, XML, PDF.

HTTP 5xx on XML/PDF is **recorded per paper** and the stream stays active so
the rest of the corpus is still probed (evidence for EPMC). Only the JSON/search
stream is disabled globally when search itself is down (preflight).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

STREAM_JSON = "json"
STREAM_XML = "xml"
STREAM_PDF = "pdf"
STREAM_NAMES = (STREAM_JSON, STREAM_XML, STREAM_PDF)

# Set by pipeline CLI preflight for the collect action to reuse.
PREFLIGHT_BOARD: Optional["EpmcStreamBoard"] = None


@dataclass
class StreamState:
    name: str
    active: bool = True
    reason: str = ""
    status_code: Optional[int] = None


@dataclass
class StreamHttpError:
    """One HTTP failure on a stream for a specific paper (or probe)."""

    stream: str
    status_code: int
    paper_id: str = ""
    url: str = ""
    detail: str = ""
    at: str = ""

    def __post_init__(self) -> None:
        if not self.at:
            self.at = datetime.now(timezone.utc).isoformat()


@dataclass
class EpmcStreamBoard:
    """Mutable board of EPMC stream health + per-call HTTP error log."""

    streams: Dict[str, StreamState] = field(default_factory=dict)
    http_errors: List[StreamHttpError] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.streams:
            self.streams = {name: StreamState(name=name) for name in STREAM_NAMES}

    def is_active(self, name: str) -> bool:
        state = self.streams.get(name)
        return bool(state and state.active)

    def disable(
        self,
        name: str,
        *,
        reason: str,
        status_code: Optional[int] = None,
    ) -> None:
        """Disable a stream for the rest of the job (use mainly for JSON/search)."""
        state = self.streams.setdefault(name, StreamState(name=name))
        if not state.active:
            return
        state.active = False
        state.reason = reason
        state.status_code = status_code

    def record_http_error(
        self,
        stream: str,
        *,
        status_code: int,
        paper_id: str = "",
        url: str = "",
        detail: str = "",
    ) -> None:
        """Log a per-paper HTTP failure; does **not** disable the stream."""
        self.http_errors.append(
            StreamHttpError(
                stream=str(stream),
                status_code=int(status_code),
                paper_id=str(paper_id or ""),
                url=str(url or ""),
                detail=str(detail or ""),
            )
        )

    def errors_for(self, stream: str) -> List[StreamHttpError]:
        return [e for e in self.http_errors if e.stream == stream]

    def error_counts_by_stream(self) -> Dict[str, int]:
        counts: Dict[str, int] = {n: 0 for n in STREAM_NAMES}
        for err in self.http_errors:
            counts[err.stream] = counts.get(err.stream, 0) + 1
        return counts

    def error_counts_by_status(
        self, stream: Optional[str] = None
    ) -> Dict[int, int]:
        """Map HTTP status → count (optionally for one stream)."""
        counts: Dict[int, int] = {}
        for err in self.http_errors:
            if stream is not None and err.stream != stream:
                continue
            code = int(err.status_code)
            counts[code] = counts.get(code, 0) + 1
        return counts

    def format_status_counts(
        self, stream: Optional[str] = None
    ) -> str:
        """Compact status tallies, e.g. ``500(3), 403(5)``."""
        counts = self.error_counts_by_status(stream)
        if not counts:
            return ""
        return ", ".join(
            f"{code}({counts[code]})" for code in sorted(counts)
        )

    def active_names(self) -> List[str]:
        return [n for n, s in self.streams.items() if s.active]

    def disabled_names(self) -> List[str]:
        return [n for n, s in self.streams.items() if not s.active]

    def summary_line(self) -> str:
        parts: List[str] = []
        counts = self.error_counts_by_stream()
        for name in STREAM_NAMES:
            state = self.streams[name]
            if state.active:
                n_err = counts.get(name, 0)
                if n_err:
                    by_status = self.format_status_counts(name)
                    parts.append(f"{name}=on({by_status or n_err})")
                else:
                    parts.append(f"{name}=on")
            else:
                code = f"{state.status_code}" if state.status_code else "off"
                parts.append(f"{name}={code}")
        return "streams " + " ".join(parts)

    def format_panel(self, *, final: bool = False) -> str:
        """Live or end-of-job stream panel.

        ``final=True`` uses Finished wording so the box does not look like
        a preflight / still-running prompt.
        """
        counts = self.error_counts_by_stream()
        title = "Europe PMC streams (done)" if final else "Europe PMC streams"
        lines = [f"┌─ {title}"]
        labels = {
            STREAM_JSON: "JSON search",
            STREAM_XML: "XML full text",
            STREAM_PDF: "PDF",
        }
        for name in STREAM_NAMES:
            state = self.streams[name]
            label = labels.get(name, name)
            if state.active:
                n_err = counts.get(name, 0)
                if n_err:
                    by_status = self.format_status_counts(name)
                    suffix = f" — HTTP {by_status}" if by_status else f" — {n_err} HTTP"
                    lines.append(f"│ {label:<14} active{suffix}")
                else:
                    lines.append(f"│ {label:<14} active")
            else:
                detail = state.reason or "disabled"
                code = f" {state.status_code}" if state.status_code else ""
                lines.append(f"│ {label:<14} off{code} — {detail}")
                if not final:
                    lines.append(
                        "│                → This stream is discontinued for now; "
                        "other streams continue."
                    )
        if self.http_errors:
            lines.append("│")
            by_status = self.format_status_counts()
            lines.append(
                f"│ HTTP errors: {by_status} "
                f"(XML={counts.get(STREAM_XML, 0)}, "
                f"PDF={counts.get(STREAM_PDF, 0)}, "
                f"JSON={counts.get(STREAM_JSON, 0)}; "
                f"total={len(self.http_errors)})"
            )
            xml_5xx = [
                e
                for e in self.http_errors
                if e.stream == STREAM_XML and e.status_code >= 500
            ]
            if xml_5xx:
                sample = ", ".join(
                    (e.paper_id or "?") for e in xml_5xx[-8:]
                )
                lines.append(f"│ Recent XML 5xx: {sample}")
        lines.append("│")
        if not self.is_active(STREAM_JSON):
            lines.append("│ JSON/search is down — cannot collect papers.")
        elif final:
            if self.http_errors:
                lines.append(
                    "│ Finished — see HTTP tallies above; full log on disk."
                )
            else:
                lines.append("│ Finished — no HTTP errors logged.")
        else:
            lines.append(
                "│ Continuing with active streams; XML/PDF 5xx do not stop probing."
            )
        lines.append("└─")
        return "\n".join(lines)

    def to_report_dict(self) -> Dict[str, Any]:
        return {
            "written_at": datetime.now(timezone.utc).isoformat(),
            "streams": {
                name: {
                    "active": state.active,
                    "reason": state.reason,
                    "status_code": state.status_code,
                }
                for name, state in self.streams.items()
            },
            "error_counts": self.error_counts_by_stream(),
            "error_counts_by_status": {
                str(k): v for k, v in sorted(self.error_counts_by_status().items())
            },
            "http_errors": [
                {
                    "stream": e.stream,
                    "status_code": e.status_code,
                    "paper_id": e.paper_id,
                    "url": e.url,
                    "detail": e.detail,
                    "at": e.at,
                }
                for e in self.http_errors
            ],
        }

    def write_error_report(self, path: Path) -> Path:
        """Write JSON report of all logged HTTP errors (for EPMC / debugging)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_report_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


def write_paper_metadata_json(
    output_dir: Path,
    paper_id: str,
    paper: dict,
) -> Path:
    """Persist search/metadata JSON as flat ``{id}.json`` (skip if present)."""
    from semantic_corpus.pipeline.flat_corpus import path_json, paper_stem

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = paper_stem(paper_id)
    path = path_json(output_dir, stem)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > 0:
        return path
    payload = dict(paper)
    payload.setdefault("paper_id", stem)
    if stem.startswith("PMC") and "pmcid" not in payload:
        payload["pmcid"] = stem
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def maybe_docling_pdf_to_xml(
    pdf_path: Path,
    xml_path: Path,
    *,
    do_ocr: bool = False,
) -> Optional[Path]:
    """Convert PDF → XML with Docling. Returns xml_path on success.

    Callers should pass ``{id}.pdf.xml`` for Docling output (never overwrite
    a good publisher ``{id}.xml``).
    """
    from semantic_corpus.repositories.document_content import (
        is_valid_document_file,
        safe_write_document,
    )

    pdf_path = Path(pdf_path)
    xml_path = Path(xml_path)
    if is_valid_document_file(xml_path, "xml"):
        return xml_path
    if not is_valid_document_file(pdf_path, "pdf"):
        return None
    try:
        from semantic_corpus.transformation.pdf_to_html import convert_pdf_to_xml
    except ImportError:
        return None
    import logging

    # Docling is chatty on stdout/stderr and corrupts the collect TTY panel.
    prev_root = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        # ``.pdf.xml`` → temp ``.pdf.xml.docling`` (Path.with_suffix would break)
        tmp = Path(str(xml_path) + ".docling")
        convert_pdf_to_xml(pdf_path, tmp, do_ocr=do_ocr)
        content = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        if not safe_write_document(xml_path, content, fmt="xml"):
            return None
        return xml_path if is_valid_document_file(xml_path, "xml") else None
    except Exception:
        return None
    finally:
        logging.disable(prev_root)


def print_stream_board(
    board: EpmcStreamBoard,
    *,
    stream: Optional[TextIO] = None,
    final: bool = False,
) -> None:
    out = stream or sys.stderr
    print(board.format_panel(final=final), file=out, flush=True)
