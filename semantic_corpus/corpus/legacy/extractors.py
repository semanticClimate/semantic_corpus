"""PDF/HTML extractors for the legacy converter.

Backends (in preference order for ``auto``):
- ``docling`` — structured HTML (tables/figures/lists when models allow)
- ``amilib`` — pdfplumber-based scholarly HTML (fonts/positions; optional extra)
- ``pymupdf`` — baseline text-layer HTML (always available if pymupdf installed)
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Union


@dataclass
class ExtractResult:
    """Raw extract before sectioner id minting."""

    html: str
    engine: str
    source_path: Path
    warnings: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class Extractor(Protocol):
    name: str

    def extract(self, path: Union[Path, str], *, outdir: Optional[Path] = None) -> ExtractResult:
        ...


def _as_path(path: Union[Path, str]) -> Path:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Input not found: {p}")
    return p


class PymupdfExtractor:
    """Baseline: page text → paragraph HTML (not scholarly structure)."""

    name = "pymupdf"

    def extract(self, path: Union[Path, str], *, outdir: Optional[Path] = None) -> ExtractResult:
        import pymupdf

        pdf_path = _as_path(path)
        doc = pymupdf.open(pdf_path)
        parts: List[str] = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'/>",
            f"<title>{html_lib.escape(pdf_path.stem)}</title></head><body>",
        ]
        warnings = [
            "pymupdf baseline: line/paragraph guess only; "
            "no reliable tables/figures/footnotes/fonts"
        ]
        for i, page in enumerate(doc, start=1):
            parts.append(f'<section data-page="{i}" class="pdf-page">')
            text = page.get_text()
            for block in re.split(r"\n\s*\n", text):
                block = block.strip()
                if not block:
                    continue
                # Soft line-join within a block: single newlines → space
                joined = re.sub(r"(?<![.-])\n(?!\n)", " ", block)
                joined = re.sub(r"\s+", " ", joined).strip()
                parts.append(f"<p>{html_lib.escape(joined)}</p>")
            parts.append("</section>")
        parts.append("</body></html>")
        html = "\n".join(parts)
        if outdir is not None:
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / f"{pdf_path.stem}.pymupdf.html").write_text(html, encoding="utf-8")
        return ExtractResult(
            html=html,
            engine=self.name,
            source_path=pdf_path,
            warnings=warnings,
            meta={"pages": doc.page_count},
        )


class DoclingExtractor:
    """Docling structured HTML export (tables/figures/lists when available)."""

    name = "docling"

    def extract(self, path: Union[Path, str], *, outdir: Optional[Path] = None) -> ExtractResult:
        from semantic_corpus.transformation.pdf_to_html import (
            convert_pdf_to_html,
            get_docling_converter,
        )

        pdf_path = _as_path(path)
        warnings: List[str] = []
        tmp_dir = outdir or Path(pdf_path.parent) / "_docling_extract"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        html_path = tmp_dir / f"{pdf_path.stem}.docling.html"
        try:
            convert_pdf_to_html(
                pdf_path,
                html_path,
                metadata={"title": pdf_path.stem},
                docling_converter=get_docling_converter(do_ocr=False),
            )
        except Exception as exc:
            raise RuntimeError(f"docling extract failed for {pdf_path}: {exc}") from exc
        html = html_path.read_text(encoding="utf-8")
        warnings.append(
            "docling: better structure than pymupdf; footnote/font-role semantics still limited"
        )
        return ExtractResult(
            html=html,
            engine=self.name,
            source_path=pdf_path,
            warnings=warnings,
            meta={"html_path": str(html_path)},
        )


class AmilibExtractor:
    """amilib HtmlGenerator PDF→HTML (positioned spans; scholarly layout path)."""

    name = "amilib"

    def extract(self, path: Union[Path, str], *, outdir: Optional[Path] = None) -> ExtractResult:
        pdf_path = _as_path(path)
        try:
            from amilib.html_generator import HtmlGenerator
            import lxml.etree as ET
        except ImportError as exc:
            raise RuntimeError(
                "amilib is not installed. pip install -e ../amilib or pip install 'semantic_corpus[legacy]'"
            ) from exc

        work = outdir or Path(pdf_path.parent) / "_amilib_extract" / pdf_path.stem
        work.mkdir(parents=True, exist_ok=True)
        html_elem = HtmlGenerator.read_pdf_convert_to_html(
            input_pdf=pdf_path,
            outdir=work,
            write=True,
            debug=False,
            max_lines=10_000_000,
            max_edges=10_000_000,
        )
        if html_elem is None:
            raise RuntimeError(f"amilib returned no HTML for {pdf_path}")
        total = work / "total_pages.html"
        if total.is_file():
            html = total.read_text(encoding="utf-8")
        else:
            root = html_elem.getroot() if hasattr(html_elem, "getroot") else html_elem
            html = ET.tostring(root, encoding="unicode", method="html")
        return ExtractResult(
            html=html,
            engine=self.name,
            source_path=pdf_path,
            warnings=[
                "amilib: use with sectioner refine for page-join / font roles where applicable"
            ],
            meta={"outdir": str(work)},
        )


class _StubExtractor:
    """Placeholder for planned backends (Marker, MinerU)."""

    def __init__(self, name: str, hint: str) -> None:
        self.name = name
        self._hint = hint

    def extract(self, path: Union[Path, str], *, outdir: Optional[Path] = None) -> ExtractResult:
        raise NotImplementedError(
            f"Extractor {self.name!r} is not wired yet. {self._hint}"
        )


AVAILABLE_EXTRACTORS: Dict[str, Callable[[], Extractor]] = {
    "pymupdf": PymupdfExtractor,
    "docling": DoclingExtractor,
    "amilib": AmilibExtractor,
    "marker": lambda: _StubExtractor(
        "marker", "Track Marker as optional extra; use docling or amilib for now."
    ),
    "mineru": lambda: _StubExtractor(
        "mineru", "Track MinerU as optional extra; use docling or amilib for now."
    ),
}


def list_extractors(*, include_stubs: bool = False) -> List[str]:
    """Return usable extractor names; probe optional imports."""
    names: List[str] = []
    try:
        import pymupdf  # noqa: F401

        names.append("pymupdf")
    except ImportError:
        pass
    try:
        import docling  # noqa: F401

        names.append("docling")
    except ImportError:
        pass
    try:
        import amilib  # noqa: F401

        names.append("amilib")
    except ImportError:
        pass
    if include_stubs:
        for stub in ("marker", "mineru"):
            if stub not in names:
                names.append(stub)
    return names


def get_extractor(name: str) -> Extractor:
    key = name.lower().strip()
    if key == "auto":
        available = list_extractors()
        for preferred in ("docling", "amilib", "pymupdf"):
            if preferred in available:
                return AVAILABLE_EXTRACTORS[preferred]()
        raise RuntimeError("No PDF extractor available (need pymupdf at minimum)")
    if key not in AVAILABLE_EXTRACTORS:
        raise ValueError(
            f"Unknown extractor {name!r}; choose from {sorted(AVAILABLE_EXTRACTORS)}"
        )
    return AVAILABLE_EXTRACTORS[key]()
