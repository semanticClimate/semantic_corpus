"""legacy PDF/HTML → indexed_text pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from semantic_corpus.corpus.legacy.extractors import ExtractResult, get_extractor
from semantic_corpus.corpus.legacy.sectioner import section_to_indexed_text


def legacy_to_indexed_text(
    path: Union[Path, str],
    *,
    extractor: str = "auto",
    paper_id: Optional[str] = None,
    id_scheme: str = "v1",
    refine: str = "auto",
    outdir: Optional[Union[Path, str]] = None,
    write_html: bool = False,
) -> Dict[str, Any]:
    """Run extractor → sectioner → indexed_text.

    Args:
        path: Input PDF (or HTML for sectioner-only: pass ``extractor="html"``).
        extractor: ``auto`` | ``pymupdf`` | ``docling`` | ``amilib`` | ``html``.
        paper_id: Document id; defaults to file stem.
        id_scheme: Stamp for skip-satisfied / consumer filters.
        refine: ``none`` | ``amilib`` | ``auto`` (page-join when amilib scripts available).
        outdir: Optional working directory for engine artefacts.
        write_html: If True and outdir set, write ``{paper_id}.indexed.html``.
    """
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(f"Input not found: {src}")
    pid = paper_id or src.stem
    work = Path(outdir) if outdir is not None else None

    if extractor.lower().strip() == "html" or src.suffix.lower() in {".html", ".htm"}:
        extract = ExtractResult(
            html=src.read_text(encoding="utf-8"),
            engine="html",
            source_path=src,
            warnings=[],
        )
    else:
        eng = get_extractor(extractor)
        extract = eng.extract(src, outdir=work)

    indexed = section_to_indexed_text(
        extract.html,
        paper_id=pid,
        id_scheme=id_scheme,
        refine=refine,
    )
    indexed["extractor"] = extract.engine
    indexed["source_path"] = str(extract.source_path)
    indexed["extract_meta"] = extract.meta
    indexed.setdefault("warnings", [])
    indexed["warnings"] = list(extract.warnings) + list(indexed.get("warnings") or [])
    indexed["type"] = "indexed_text"

    if write_html and work is not None:
        work.mkdir(parents=True, exist_ok=True)
        html_out = work / f"{pid}.indexed.html"
        html_out.write_text(indexed["html"], encoding="utf-8")
        indexed["indexed_html_path"] = str(html_out)
        meta_out = work / f"{pid}.indexed.json"
        meta_out.write_text(
            json.dumps(
                {
                    "paper_id": indexed["paper_id"],
                    "id_scheme": indexed["id_scheme"],
                    "extractor": indexed["extractor"],
                    "blocks": indexed["blocks"],
                    "warnings": indexed["warnings"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    return indexed
