"""Step 1: load an existing BAGIT corpus for cluster review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_corpus,
    export_review_tables,
)

# Demo presets relative to project root (cwd when running app/examples)
DEMO_BAGIT_CORPORA = {
    "step0_live_demo": Path("corpora", "step0_live_demo"),
    "climate_anxiety_2026": Path("corpora", "climate_anxiety_2026"),
    "climate_change_2026": Path("corpora", "climate_change_2026"),
    "aqi_india_pilot": Path("corpora", "aqi_india_pilot"),
    "ocean_heatwaves_2026": Path("corpora", "ocean_heatwaves_2026"),
}


def resolve_bagit_root(corpus_dir: Path) -> Path:
    """Return the directory that contains bagit.txt (may be corpus_dir itself)."""
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise CorpusError(f"Corpus path not found: {corpus_dir}")
    if Path(corpus_dir, "bagit.txt").is_file():
        return corpus_dir
    # Nested bag (historical data/data layout)
    nested = Path(corpus_dir, "data")
    if Path(nested, "bagit.txt").is_file():
        return nested
    raise CorpusError(
        f"Not a BAGIT corpus (no bagit.txt under {corpus_dir} or {corpus_dir}/data)"
    )


def find_metadata_dir(bag_root: Path) -> Path:
    """Locate metadata directory, tolerating nested data/data/ payloads."""
    bag_root = Path(bag_root)
    candidates = [
        Path(bag_root, "data", "metadata"),
        Path(bag_root, "data", "data", "metadata"),
        Path(bag_root, "metadata"),
    ]
    for path in candidates:
        if path.is_dir() and any(path.glob("*_metadata.json")):
            return path
    # Empty but correctly placed bag
    preferred = Path(bag_root, "data", "metadata")
    if preferred.is_dir():
        return preferred
    raise CorpusError(f"No metadata directory with *_metadata.json under {bag_root}")


def find_review_table(corpus_dir: Path, bag_root: Path) -> Optional[Path]:
    """Find an existing review_table.json near the corpus, if any."""
    candidates = [
        Path(corpus_dir, "review", "review_table.json"),
        Path(bag_root, "review", "review_table.json"),
        Path(bag_root, "data", "analysis", "review", "review_table.json"),
        Path(corpus_dir, "data", "analysis", "review", "review_table.json"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _paper_ids_from_metadata_dir(metadata_dir: Path) -> List[str]:
    ids: List[str] = []
    for metadata_file in sorted(metadata_dir.glob("*_metadata.json")):
        stem = metadata_file.stem
        if stem.endswith("_metadata"):
            ids.append(stem[: -len("_metadata")])
        else:
            ids.append(stem.replace("_metadata", ""))
    return ids


def _load_metadata(metadata_dir: Path, paper_id: str) -> Dict[str, Any]:
    path = Path(metadata_dir, f"{paper_id}_metadata.json")
    if not path.is_file():
        raise CorpusError(f"Missing metadata for {paper_id}: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _open_corpus_manager(bag_root: Path) -> CorpusManager:
    """Open existing bag without nesting (create_bag is a no-op if bagit.txt exists)."""
    return CorpusManager(bag_root, use_bagit=True)


def list_demo_corpora(project_root: Optional[Path] = None) -> Dict[str, Path]:
    """Return demo name → absolute path for presets that exist on disk."""
    root = Path(project_root) if project_root else Path.cwd()
    found: Dict[str, Path] = {}
    for name, rel in DEMO_BAGIT_CORPORA.items():
        path = Path(root, rel)
        if Path(path, "bagit.txt").is_file() or Path(path, "data", "bagit.txt").is_file():
            found[name] = path.resolve()
    return found


def load_bagit_corpus(
    corpus_dir: Path,
    *,
    review_table_path: Optional[Path] = None,
    query_name: str = "",
    query_string: str = "",
    write_review_if_missing: bool = True,
) -> Dict[str, Any]:
    """Load an existing BAGIT corpus for cluster-review Step 1.

    Args:
        corpus_dir: Path to bag root or parent that contains bagit.txt / data/bagit.txt.
        review_table_path: Optional explicit review_table.json.
        query_name / query_string: Used when building a fresh review table.
        write_review_if_missing: If no review table found, build one under
            ``<corpus_dir>/review/``.

    Returns:
        Summary with paper list, review rows, and resolved paths.
    """
    corpus_dir = Path(corpus_dir)
    bag_root = resolve_bagit_root(corpus_dir)
    metadata_dir = find_metadata_dir(bag_root)
    paper_ids = _paper_ids_from_metadata_dir(metadata_dir)

    # Prefer CorpusManager when metadata sits at the expected data/metadata path
    corpus = _open_corpus_manager(bag_root)
    manager_ids = corpus.list_papers()
    if not manager_ids and paper_ids:
        # Nested payload: build rows from metadata files directly
        rows = []
        from semantic_corpus.corpus_review.relevance_scorer import score_paper_relevance
        from semantic_corpus.corpus_review.review_schema import make_review_row
        from semantic_corpus.corpus_review.review_table import _paper_has_file

        for paper_id in paper_ids:
            metadata = _load_metadata(metadata_dir, paper_id)
            has_xml = _paper_has_file(bag_root, paper_id, "xml")
            has_html = _paper_has_file(bag_root, paper_id, "html")
            has_pdf = _paper_has_file(bag_root, paper_id, "pdf")
            # Also check nested documents path
            if not has_xml:
                has_xml = Path(
                    bag_root, "data", "data", "documents", "xml", f"{paper_id}.xml"
                ).is_file() or Path(
                    bag_root, "data", "documents", "xml", f"{paper_id}.xml"
                ).is_file()
            if not has_pdf:
                has_pdf = Path(
                    bag_root, "data", "data", "documents", "pdf", f"{paper_id}.pdf"
                ).is_file() or Path(
                    bag_root, "data", "documents", "pdf", f"{paper_id}.pdf"
                ).is_file()
            score, matched = score_paper_relevance(
                metadata, has_xml=(has_xml or has_html), has_pdf=has_pdf
            )
            rows.append(
                make_review_row(
                    paper_id=paper_id,
                    metadata=metadata,
                    score=score,
                    location_terms=matched["location_terms"],
                    pollutant_terms=matched["pollutant_terms"],
                    health_terms=matched["health_terms"],
                    has_xml=has_xml,
                    has_html=has_html,
                    has_pdf=has_pdf,
                    query_name=query_name,
                    query_string=query_string,
                )
            )
        rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
        effective_ids = paper_ids
    else:
        rows = build_review_rows_from_corpus(
            corpus, query_name=query_name, query_string=query_string
        )
        effective_ids = manager_ids or paper_ids

    existing_review = (
        Path(review_table_path)
        if review_table_path
        else find_review_table(corpus_dir, bag_root)
    )
    review_source = "built_from_corpus"
    if existing_review and existing_review.is_file():
        with open(existing_review, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, list) and loaded:
            rows = loaded
            review_source = str(existing_review.resolve())

    review_paths: Dict[str, str] = {}
    review_dir = Path(corpus_dir, "review")
    if write_review_if_missing and review_source == "built_from_corpus":
        review_dir.mkdir(parents=True, exist_ok=True)
        paths = export_review_tables(rows, review_dir)
        review_paths = {k: str(Path(v).resolve()) for k, v in paths.items()}
    elif existing_review:
        review_paths = {"json": str(Path(existing_review).resolve())}

    papers_preview: List[Dict[str, Any]] = []
    by_id = {r.get("paper_id"): r for r in rows}
    for paper_id in sorted(effective_ids):
        row = by_id.get(paper_id) or {}
        meta = {}
        try:
            meta = _load_metadata(metadata_dir, paper_id)
        except CorpusError:
            meta = {}
        papers_preview.append(
            {
                "paper_id": paper_id,
                "title": row.get("title") or meta.get("title") or "",
                "review_status": row.get("review_status") or "review",
                "has_xml": bool(row.get("has_xml")),
                "has_pdf": bool(row.get("has_pdf")),
                "publication_date": row.get("publication_date")
                or meta.get("publication_date")
                or "",
            }
        )

    return {
        "step": 1,
        "corpus_dir": str(corpus_dir.resolve()),
        "bag_root": str(bag_root.resolve()),
        "metadata_dir": str(metadata_dir.resolve()),
        "paper_count": len(effective_ids),
        "paper_ids": sorted(effective_ids),
        "papers": papers_preview,
        "row_count": len(rows),
        "rows": rows,
        "review_source": review_source,
        "review_paths": review_paths,
        "query_name": query_name,
        "query_string": query_string,
    }
