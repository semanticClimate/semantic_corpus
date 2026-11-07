"""Real step actions for the pipeline.

Design spine: collect → corpus → phrases → clusters[--kg] → clean → encyclopedia[--kg].
Set ``PIPELINE_PLACEHOLDER=1`` to force stamp-only behaviour (unit tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import os

from semantic_corpus.pipeline.config import (
    DEFAULT_LIMIT,
    ENV_PLACEHOLDER,
    options_from_env,
)
from semantic_corpus.pipeline.placeholders import run_placeholder, stamp_path, write_stamp
from semantic_corpus.utils import get_project_temp_dir


def use_placeholders() -> bool:
    return os.environ.get(ENV_PLACEHOLDER, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _stamp(step: str, extra: Optional[Dict[str, Any]] = None) -> Path:
    opts = options_from_env()
    return write_stamp(step, opts.workdir, extra={"status": "ok", **(extra or {})})


def _query_dirs():
    opts = options_from_env()
    workdir = opts.workdir
    query_name = workdir.name
    query_dir = Path(get_project_temp_dir(), "queries", query_name)
    return workdir, query_name, query_dir


def run_collect() -> Dict[str, Any]:
    """Collect via remotes (--query) or static documents (--source)."""
    if use_placeholders():
        return run_placeholder("collect")

    opts = options_from_env()
    if opts.query and opts.source:
        raise ValueError("Use either --query or --source, not both")
    if opts.source:
        raise NotImplementedError(
            "collect --source (static documents) is not wired yet; "
            "use --query for remotes, or point --workdir at an existing bag"
        )
    if not opts.query:
        raise ValueError(
            "collect requires --query (EPMC/other remotes) or --source (static docs)"
        )

    from semantic_corpus.cluster_review.step0 import create_corpus_from_query

    workdir, query_name, query_dir = _query_dirs()
    workdir.mkdir(parents=True, exist_ok=True)
    print(
        f"[pipeline] collect: searching {opts.query!r} "
        f"limit={opts.limit} repository={opts.repository!r}"
    )
    summary = create_corpus_from_query(
        query_string=opts.query,
        query_name=query_name,
        query_dir=query_dir,
        repositories=opts.repository or "europe_pmc",
        limit=int(opts.limit or DEFAULT_LIMIT),
        formats=["xml"],
        corpus_dir=workdir,
        create_bagit=True,
    )
    paper_count = summary.get("bagit_paper_count") or summary.get("result_count")
    index_summary = _ensure_packet_indexes(workdir)
    counts = index_summary.get("counts") or {}
    _stamp(
        "collect",
        {
            "mode": "remote",
            "query_dir": str(query_dir),
            "downloaded_count": summary.get("downloaded_count"),
            "paper_count": paper_count,
            "bagit_paper_ids": summary.get("bagit_paper_ids"),
        },
    )
    _stamp(
        "corpus",
        {
            "produced_by": "collect",
            "bagit": str(workdir / "bagit.txt"),
            "paper_count": paper_count,
            "packets_manifest": index_summary.get("manifest_path"),
            "containers": counts.get("containers"),
            "packets": counts.get("packets"),
        },
    )
    print(
        f"[pipeline] collect: done ({paper_count} papers; "
        f"packets={counts.get('packets')}) → {workdir}"
    )
    return summary


def _ensure_packet_indexes(workdir: Path) -> Dict[str, Any]:
    """Structural indexes on text components (part of corpus, not a separate step)."""
    from semantic_corpus.cluster_review.packets import build_packet_index

    return build_packet_index(workdir)


def run_corpus() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("corpus")

    from semantic_corpus.cluster_review.step1 import load_bagit_corpus

    opts = options_from_env()
    workdir = opts.workdir
    if not (workdir / "bagit.txt").is_file():
        raise FileNotFoundError(
            f"No BAGIT corpus at {workdir}. "
            "Run with --query or --source first, or point --workdir at an existing bag."
        )
    print(f"[pipeline] corpus: loading {workdir}")
    summary = load_bagit_corpus(workdir, write_review_if_missing=True)
    print(f"[pipeline] corpus: ensuring packet indexes")
    index_summary = _ensure_packet_indexes(workdir)
    counts = index_summary.get("counts") or {}
    _stamp(
        "corpus",
        {
            "paper_count": summary.get("paper_count"),
            "bag_root": summary.get("bag_root") or str(workdir),
            "packets_manifest": index_summary.get("manifest_path"),
            "containers": counts.get("containers"),
            "packets": counts.get("packets"),
        },
    )
    print(
        f"[pipeline] corpus: {summary.get('paper_count')} papers; "
        f"packets={counts.get('packets')} → {index_summary.get('manifest_path')}"
    )
    summary = dict(summary)
    summary["packet_index"] = index_summary
    return summary


def run_phrases() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("phrases")

    from semantic_corpus.cluster_review.step2 import extract_phrases

    opts = options_from_env()
    print(
        f"[pipeline] phrases: traverse packet texts; "
        f"method={opts.phrase_method} n={opts.phrase_n} top={opts.phrase_top}"
    )
    summary = extract_phrases(
        opts.workdir,
        method=opts.phrase_method,
        n=opts.phrase_n,
        top=opts.phrase_top,
        use_cache=True,
        force=False,
    )
    _stamp(
        "phrases",
        {
            "paper_count": summary.get("paper_count"),
            "index": str(opts.workdir / "phrases" / "index.json"),
        },
    )
    print(f"[pipeline] phrases: done ({summary.get('paper_count')} papers)")
    return summary


def run_pdfs() -> Dict[str, Any]:
    return run_placeholder("pdfs")


def _emit_display_kg(stage: str) -> Optional[Dict[str, Any]]:
    """Write/open display KG after clusters (plain) or encyclopedia (annotated).

    Not a pipeline step — cheap view assembly controlled by ``--kg`` / ``--no-kg``.
    """
    opts = options_from_env()
    if not opts.write_kg:
        print(f"[pipeline] {stage}: --no-kg (skip display graph)")
        return None
    if use_placeholders():
        print(f"[pipeline] {stage}: kg placeholder (stage={stage})")
        return {"status": "placeholder", "stage": stage}

    from semantic_corpus.cluster_review.kg import build_kg

    if stage == "clusters":
        # Unannotated incidence graph only.
        links: tuple = ("clusters",)
    else:
        # Annotated: keep user --kg-links; default clusters, add wikipedia if present.
        links = opts.kg_link_list()
        enc = opts.workdir / "encyclopedia" / "entries.json"
        if enc.is_file() and "wikipedia" not in links and "wikidata" not in links:
            links = tuple(list(links) + ["wikipedia"])

    max_terms = opts.effective_kg_max_terms()
    print(
        f"[pipeline] {stage}: kg links={','.join(links)} "
        f"min_paper_count={opts.kg_min_paper_count} max_terms={max_terms} "
        f"document_limit={opts.document_limit} max_island={opts.kg_max_island}"
    )
    summary = build_kg(
        opts.workdir,
        kg_links=links,
        max_island=int(opts.kg_max_island),
        min_paper_count=int(opts.kg_min_paper_count),
        max_terms=int(max_terms),
        document_limit=opts.document_limit,
        write_html=True,
        open_browser=bool(opts.kg_open),
    )
    counts = summary.get("counts") or {}
    print(
        f"[pipeline] {stage}: kg nodes={counts.get('nodes')} "
        f"edges={counts.get('edges')} terms={counts.get('terms')} "
        f"islands={counts.get('islands')} html={summary.get('html_path')}"
    )
    summary = dict(summary)
    summary["kg_stage"] = stage
    return summary


def run_clusters() -> Dict[str, Any]:
    if use_placeholders():
        summary = run_placeholder("clusters")
        kg = _emit_display_kg("clusters")
        if kg:
            summary = dict(summary)
            summary["kg"] = kg
        return summary

    from semantic_corpus.cluster_review.step3 import build_clusters

    opts = options_from_env()
    print(
        f"[pipeline] clusters: algorithm={opts.cluster_algorithm} "
        f"resolution={opts.cluster_resolution}"
    )
    summary = build_clusters(
        opts.workdir,
        algorithm=opts.cluster_algorithm,
        resolution=float(opts.cluster_resolution),
    )
    kg = _emit_display_kg("clusters")
    extra: Dict[str, Any] = {
        "cluster_count": summary.get("cluster_count"),
        "paper_count": summary.get("paper_count"),
        "graph_summary": str(opts.workdir / "clusters" / "graph_summary.json"),
        "write_kg": bool(opts.write_kg),
    }
    if kg and kg.get("html_path"):
        extra["kg_html"] = kg.get("html_path")
        extra["kg_graph"] = kg.get("graph_path")
    _stamp("clusters", extra)
    print(f"[pipeline] clusters: {summary.get('cluster_count')} clusters")
    summary = dict(summary)
    if kg:
        summary["kg"] = kg
    return summary


def run_clean() -> Dict[str, Any]:
    return run_placeholder("clean")


def run_encyclopedia() -> Dict[str, Any]:
    if use_placeholders():
        summary = run_placeholder("encyclopedia")
        kg = _emit_display_kg("encyclopedia")
        if kg:
            summary = dict(summary)
            summary["kg"] = kg
        return summary

    from semantic_corpus.cluster_review.encyclopedia import build_encyclopedia

    opts = options_from_env()
    phrase_limit = opts.effective_phrase_limit()
    print(
        f"[pipeline] encyclopedia: lang={opts.encyclopedia_lang} "
        f"phrase_limit={phrase_limit} min_score={opts.min_score} "
        f"min_paper_count={opts.min_paper_count} "
        f"document_limit={opts.document_limit} from={opts.encyclopedia_source}"
    )
    summary = build_encyclopedia(
        opts.workdir,
        lang=opts.encyclopedia_lang,
        max_entries=int(phrase_limit),
        min_score=float(opts.min_score),
        min_paper_count=int(opts.min_paper_count),
        source=opts.encyclopedia_source,
        document_limit=opts.document_limit,
        force=False,
        write_html=True,
        fetch_html_descriptions=True,
    )
    kg = _emit_display_kg("encyclopedia")
    counts = summary.get("counts") or {}
    extra = {
        "entries_path": summary.get("entries_path"),
        "html_path": summary.get("html_path"),
        "selected": counts.get("selected"),
        "resolved": counts.get("resolved"),
        "ambiguous": counts.get("ambiguous"),
        "missing": counts.get("missing"),
        "error": counts.get("error"),
        "disambiguated": counts.get("disambiguated"),
        "phrase_source": (summary.get("params") or {}).get("phrase_source"),
        "write_kg": bool(opts.write_kg),
    }
    if kg and kg.get("html_path"):
        extra["kg_html"] = kg.get("html_path")
        extra["kg_graph"] = kg.get("graph_path")
    _stamp("encyclopedia", extra)
    html_note = f" html={summary.get('html_path')}" if summary.get("html_path") else ""
    print(
        f"[pipeline] encyclopedia: selected={counts.get('selected')} "
        f"resolved={counts.get('resolved')} missing={counts.get('missing')} "
        f"disambiguated={counts.get('disambiguated')} "
        f"error={counts.get('error')}{html_note}"
    )
    summary = dict(summary)
    if kg:
        summary["kg"] = kg
    return summary


STEP_ACTIONS = {
    "collect": run_collect,
    "corpus": run_corpus,
    "phrases": run_phrases,
    "pdfs": run_pdfs,
    "clusters": run_clusters,
    "clean": run_clean,
    "encyclopedia": run_encyclopedia,
}


def run_step(step: str) -> Dict[str, Any]:
    action = STEP_ACTIONS.get(step)
    if action is None:
        raise KeyError(f"No action for step {step!r}")
    return action()


def is_step_current(step: str) -> bool:
    """Uptodate: stamp exists; real mode also requires key artifacts."""
    opts = options_from_env()
    workdir = opts.workdir
    if not stamp_path(step, workdir).is_file():
        return False
    if use_placeholders():
        return True
    if step == "collect":
        return (workdir / "bagit.txt").is_file()
    if step == "corpus":
        from semantic_corpus.cluster_review.packets import packet_index_is_current

        return (workdir / "bagit.txt").is_file() and packet_index_is_current(
            workdir
        )
    if step == "phrases":
        return (workdir / "phrases" / "index.json").is_file()
    if step == "encyclopedia":
        from semantic_corpus.cluster_review.encyclopedia import encyclopedia_is_current

        return encyclopedia_is_current(
            workdir,
            lang=opts.encyclopedia_lang,
            max_entries=int(opts.effective_phrase_limit()),
            min_score=float(opts.min_score),
            min_paper_count=int(opts.min_paper_count),
            source=opts.encyclopedia_source,
            document_limit=opts.document_limit,
        )
    if step == "clusters":
        return (workdir / "clusters" / "graph_summary.json").is_file()
    return True
