"""Build encyclopedia HTML via the sibling ``encyclopedia`` package.

Reuses ``AmiEncyclopedia.save_wiki_normalized_html`` (and optionally
``add_wikipedia_descriptions_to_encyclopedia``) from
https://github.com/semanticClimate/encyclopedia.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from semantic_corpus.core.exceptions import CorpusError

DEFAULT_HTML_NAME = "encyclopedia.html"


def html_path(workdir: Path, name: str = DEFAULT_HTML_NAME) -> Path:
    return Path(workdir) / "encyclopedia" / name


def ensure_encyclopedia_on_path() -> None:
    """Make ``encyclopedia`` importable (installed package or sibling checkout)."""
    try:
        import encyclopedia  # noqa: F401

        return
    except ImportError:
        pass

    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "encyclopedia",
        Path.cwd().parent / "encyclopedia",
        here.parents[3] / "encyclopedia",  # …/workspace/encyclopedia
        here.parents[2] / "encyclopedia",
    ]
    for cand in candidates:
        if cand.is_dir() and (cand / "encyclopedia").is_dir():
            path = str(cand.resolve())
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                import encyclopedia  # noqa: F401

                return
            except ImportError:
                continue
    raise CorpusError(
        "The 'encyclopedia' package is required to write HTML.\n"
        "Install it (pip install -e ../encyclopedia) or clone\n"
        "  https://github.com/semanticClimate/encyclopedia\n"
        "next to this repo so ../encyclopedia is importable."
    )


def entries_to_ami_dicts(
    entries: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Map pipeline ``entries.json`` rows to AmiEncyclopedia entry dicts."""
    out: List[Dict[str, Any]] = []
    for item in entries or []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status == "error":
            continue
        phrase = str(item.get("phrase") or "").strip()
        if not phrase:
            continue
        display = str(
            item.get("display")
            or item.get("wiki_title")
            or phrase
        ).strip()
        wiki_url = item.get("wiki_url") or ""
        wikidata_id = item.get("wikidata_id") or ""
        if status == "missing":
            wiki_url = ""
            wikidata_id = ""
        row: Dict[str, Any] = {
            "term": display,
            "search_term": phrase,
            "search_terms": [phrase],
            "synonyms": [display] if display else [phrase],
            "wikipedia_url": wiki_url,
            "wikidata_id": wikidata_id,
            "description_html": item.get("description_html") or "",
            "definition_html": item.get("definition_html") or "",
            "pipeline_status": status,
        }
        out.append(row)
    return out


def write_encyclopedia_html(
    workdir: Path,
    *,
    entries_doc: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
    output_name: str = DEFAULT_HTML_NAME,
    fetch_descriptions: bool = True,
    verbose: bool = False,
) -> Path:
    """Write ``encyclopedia/encyclopedia.html`` from ``entries.json``.

    Uses AmiEncyclopedia from the encyclopedia repo. When
    ``fetch_descriptions`` is True, pulls first-paragraph Wikipedia text
    for entries that lack ``description_html`` (network).
    """
    ensure_encyclopedia_on_path()
    from encyclopedia.core.encyclopedia import AmiEncyclopedia
    from encyclopedia.utils.encyclopedia_builder import (
        add_wikipedia_descriptions_to_encyclopedia,
    )

    workdir = Path(workdir)
    if entries_doc is None:
        from semantic_corpus.cluster_review.encyclopedia import load_entries

        entries_doc = load_entries(workdir)
    if not entries_doc:
        raise CorpusError(f"No encyclopedia entries.json under {workdir}")

    ami_entries = entries_to_ami_dicts(entries_doc.get("entries") or [])
    enc_title = title or f"Encyclopedia ({workdir.name})"
    encyclopedia = AmiEncyclopedia(title=enc_title)
    encyclopedia.entries = ami_entries

    if fetch_descriptions and ami_entries:
        encyclopedia, _stats = add_wikipedia_descriptions_to_encyclopedia(
            encyclopedia, batch_size=5, verbose=verbose
        )

    encyclopedia.normalize_by_wikidata_id()
    encyclopedia.merge()

    out = html_path(workdir, output_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    encyclopedia.save_wiki_normalized_html(out)
    return out
