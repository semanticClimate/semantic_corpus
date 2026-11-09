"""Independent Europe PMC content streams: JSON, XML, PDF.

A HTTP 500 (or equivalent) disables **only** that stream for the rest of the
job. Other streams keep running. If XML is blocked but PDF is available,
Docling can synthesize XML from the PDF.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TextIO

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
class EpmcStreamBoard:
    """Mutable board of which EPMC streams are still active."""

    streams: Dict[str, StreamState] = field(default_factory=dict)

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
        state = self.streams.setdefault(name, StreamState(name=name))
        if not state.active:
            return
        state.active = False
        state.reason = reason
        state.status_code = status_code

    def active_names(self) -> List[str]:
        return [n for n, s in self.streams.items() if s.active]

    def disabled_names(self) -> List[str]:
        return [n for n, s in self.streams.items() if not s.active]

    def summary_line(self) -> str:
        parts: List[str] = []
        for name in STREAM_NAMES:
            state = self.streams[name]
            if state.active:
                parts.append(f"{name}=on")
            else:
                code = f"{state.status_code}" if state.status_code else "off"
                parts.append(f"{name}={code}")
        return "streams " + " ".join(parts)

    def format_panel(self) -> str:
        lines = ["┌─ EPMC streams"]
        for name in STREAM_NAMES:
            state = self.streams[name]
            if state.active:
                lines.append(f"│ {name.upper():<4}  active")
            else:
                detail = state.reason or "disabled"
                code = f" ({state.status_code})" if state.status_code else ""
                lines.append(f"│ {name.upper():<4}  off{code} — {detail}")
        if not self.is_active(STREAM_JSON):
            lines.append("│")
            lines.append("│ JSON/search is down — cannot collect papers.")
        elif not self.is_active(STREAM_XML) and self.is_active(STREAM_PDF):
            lines.append("│")
            lines.append("│ XML off — will use PDF (+ Docling → XML) when possible.")
        elif not self.is_active(STREAM_XML) and not self.is_active(STREAM_PDF):
            lines.append("│")
            lines.append("│ XML and PDF off — abstracts/metadata only.")
        lines.append("└─")
        return "\n".join(lines)


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
    board: EpmcStreamBoard, *, stream: Optional[TextIO] = None
) -> None:
    out = stream or sys.stderr
    print(board.format_panel(), file=out, flush=True)
