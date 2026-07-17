"""Export semantic_corpus to chatbot-ready manifest (contract implementation)."""

import json
from pathlib import Path
from typing import Any, Dict, List

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import REVIEW_STATUS_INCLUDE
from semantic_corpus.corpus_review.review_schema import filter_rows_by_status


def _first_author_display(authors: List[Any]) -> str:
    """Extract a short lead author name from string or Europe PMC author dict."""
    if not authors:
        return "Unknown"
    first = authors[0]
    if isinstance(first, str):
        return first.split(",")[0].strip() if "," in first else first.strip()
    if isinstance(first, dict):
        last = (first.get("lastName") or "").strip()
        if last:
            return last
        full = (first.get("fullName") or "").strip()
        if full:
            return full.split()[0]
    return "Unknown"


def build_citation_label(metadata: Dict[str, Any]) -> str:
    """Human-readable citation label for chatbot source display."""
    lead = _first_author_display(metadata.get("authors") or [])
    year = (metadata.get("publication_date") or "")[:4] or "n.d."
    title = metadata.get("title") or "Untitled"
    return f"{lead} ({year}). {title}"


def build_paper_export_record(
    paper_id: str,
    metadata: Dict[str, Any],
    corpus_dir: Path,
) -> Dict[str, Any]:
    """One paper entry in the chatbot export manifest."""
    xml_path = Path(corpus_dir, "data", "documents", "xml", f"{paper_id}.xml")
    pdf_path = Path(corpus_dir, "data", "documents", "pdf", f"{paper_id}.pdf")
    return {
        "source_id": paper_id,
        "citation_label": build_citation_label(metadata),
        "title": metadata.get("title") or "",
        "abstract": metadata.get("abstract") or "",
        "doi": metadata.get("doi") or "",
        "pmcid": metadata.get("pmcid") or "",
        "pmid": metadata.get("pmid") or "",
        "publication_date": metadata.get("publication_date") or "",
        "journal": metadata.get("journal") or "",
        "authors": metadata.get("authors") or [],
        "xml_path": str(xml_path) if xml_path.is_file() else "",
        "pdf_path": str(pdf_path) if pdf_path.is_file() else "",
        "metadata_path": str(
            Path(corpus_dir, "data", "metadata", f"{paper_id}_metadata.json")
        ),
    }


def export_corpus_for_chatbot(
    corpus: CorpusManager,
    output_dir: Path,
    *,
    included_paper_ids: List[str] = None,
    review_rows: List[Dict[str, Any]] = None,
    include_only_status: bool = True,
) -> Path:
    """Export corpus manifest for ../chatbot ingestion.

    Contract: manifest JSON with corpus metadata and per-paper source records
    (citation_label, identifiers, paths to xml/pdf/metadata). Chatbot indexer
    reads manifest and chunks from xml_path or abstract text.

    If review_rows provided and include_only_status, only papers with
    review_status == include are exported. Otherwise all corpus papers or
    included_paper_ids list is used.
    """
    if not corpus.use_bagit:
        raise CorpusError("Chatbot export requires BAGIT corpus (use_bagit=True)")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if review_rows and include_only_status:
        paper_ids = [
            r["paper_id"]
            for r in filter_rows_by_status(review_rows, REVIEW_STATUS_INCLUDE)
        ]
    elif included_paper_ids is not None:
        paper_ids = list(included_paper_ids)
    else:
        paper_ids = corpus.list_papers()

    papers: List[Dict[str, Any]] = []
    for paper_id in paper_ids:
        metadata = corpus.get_paper_metadata(paper_id)
        papers.append(
            build_paper_export_record(paper_id, metadata, corpus.corpus_dir)
        )

    manifest: Dict[str, Any] = {
        "export_version": "1.0",
        "corpus_dir": str(corpus.corpus_dir),
        "paper_count": len(papers),
        "papers": papers,
        "chunking_hint": {
            "primary_text_source": "xml_path",
            "fallback_text_source": "abstract",
            "metadata_fields_for_retrieval": [
                "title",
                "abstract",
                "doi",
                "pmcid",
                "citation_label",
            ],
        },
    }

    out_path = Path(output_dir, "chatbot_manifest.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    return out_path
