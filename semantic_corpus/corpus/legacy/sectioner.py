"""Sectioner: structure HTML into indexed_text (ids included).

Optional amilib PageJoiner refine when sibling amilib scripts are available.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Tuple

from semantic_corpus.corpus.converters.html_to_semantic import mint_text_block_ids_in_html


def _candidate_page_joiner_paths() -> List[Path]:
    """Locate page_joiner.py (not yet shipped inside the amilib package)."""
    here = Path(__file__).resolve()
    # semantic_corpus/corpus/legacy → repo root → sibling amilib
    repo_root = here.parents[3]
    workspace = here.parents[4] if len(here.parents) > 4 else repo_root.parent
    return [
        workspace / "amilib" / "scripts" / "glossary_processor" / "page_joiner.py",
        repo_root.parent / "amilib" / "scripts" / "glossary_processor" / "page_joiner.py",
        Path.home() / "workspace" / "amilib" / "scripts" / "glossary_processor" / "page_joiner.py",
    ]


def _load_page_joiner():
    """Import PageJoiner from amilib scripts if present; else None."""
    for path in _candidate_page_joiner_paths():
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(
            "amilib_page_joiner_legacy", path
        )
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue
        joiner = getattr(mod, "PageJoiner", None)
        if joiner is not None:
            return joiner
    return None


def amilib_refine_available() -> bool:
    return _load_page_joiner() is not None


def refine_html_amilib(html: str) -> Tuple[str, List[str]]:
    """Apply amilib PageJoiner when HTML has positioned divs.

    Returns:
        (html, warnings)
    """
    joiner_cls = _load_page_joiner()
    if joiner_cls is None:
        return html, [
            "amilib PageJoiner not found (install sibling amilib checkout with scripts/)"
        ]

    try:
        import lxml.etree as ET
    except ImportError:
        return html, ["lxml required for amilib refine"]

    try:
        parser = ET.HTMLParser()
        root = ET.fromstring(html.encode("utf-8"), parser=parser)
        if root is None:
            return html, ["amilib refine: empty parse"]
        joiner_cls.join_pages(root)
        out = ET.tostring(root, encoding="unicode", method="html")
        return out, ["amilib PageJoiner applied"]
    except Exception as exc:
        return html, [f"amilib refine failed: {exc}"]


def section_to_indexed_text(
    html: str,
    *,
    paper_id: str = "doc",
    id_scheme: str = "v1",
    refine: str = "auto",
) -> Dict[str, Any]:
    """Section HTML and mint text_block ids → indexed_text payload.

    Args:
        html: Extracted HTML string.
        paper_id: Document id prefix.
        id_scheme: Id scheme stamp.
        refine: ``none`` | ``amilib`` | ``auto`` (amilib if scripts available).
    """
    warnings: List[str] = []
    working = html
    want = refine.lower().strip()
    if want == "amilib":
        if not amilib_refine_available():
            warnings.append("refine=amilib requested but PageJoiner not available")
        else:
            working, w = refine_html_amilib(working)
            warnings.extend(w)
    elif want == "auto" and amilib_refine_available():
        # Only useful when extract has positioned divs (amilib HTML)
        if 'left="' in html or " left=" in html:
            working, w = refine_html_amilib(working)
            warnings.extend(w)

    indexed = mint_text_block_ids_in_html(
        working, paper_id=paper_id, id_scheme=id_scheme
    )
    indexed["warnings"] = warnings
    indexed["type"] = "indexed_text"
    return indexed
