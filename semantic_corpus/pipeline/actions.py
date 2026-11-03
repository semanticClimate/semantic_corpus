"""Real step actions for the pipeline (query → corpus → phrases → clusters).

Other steps still use placeholders until wired.
Set ``PIPELINE_PLACEHOLDER=1`` to force stamp-only behaviour (unit tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import os

from semantic_corpus.pipeline.config import ENV_PLACEHOLDER, options_from_env
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


def run_query() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("query")

    from semantic_corpus.cluster_review.step0 import create_corpus_from_query

    opts = options_from_env()
    if not opts.query:
        raise ValueError("--query is required for the query step")
    workdir, query_name, query_dir = _query_dirs()
    workdir.mkdir(parents=True, exist_ok=True)
    print(
        f"[pipeline] query: searching {opts.query!r} "
        f"limit={opts.limit} repository={opts.repository!r}"
    )
    summary = create_corpus_from_query(
        query_string=opts.query,
        query_name=query_name,
        query_dir=query_dir,
        repositories=opts.repository or "europe_pmc",
        limit=int(opts.limit or 50),
        formats=["xml"],
        corpus_dir=workdir,
        create_bagit=True,
    )
    paper_count = summary.get("bagit_paper_count") or summary.get("result_count")
    _stamp(
        "query",
        {
            "query_dir": str(query_dir),
            "downloaded_count": summary.get("downloaded_count"),
            "paper_count": paper_count,
            "bagit_paper_ids": summary.get("bagit_paper_ids"),
        },
    )
    _stamp(
        "corpus",
        {
            "produced_by": "query",
            "bagit": str(workdir / "bagit.txt"),
            "paper_count": paper_count,
        },
    )
    print(f"[pipeline] query: done ({paper_count} papers) → {workdir}")
    return summary


def run_documents() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("documents")
    return run_placeholder("documents")


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
    _stamp(
        "corpus",
        {
            "paper_count": summary.get("paper_count"),
            "bag_root": summary.get("bag_root") or str(workdir),
        },
    )
    print(f"[pipeline] corpus: {summary.get('paper_count')} papers")
    return summary


def run_phrases() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("phrases")

    from semantic_corpus.cluster_review.step2 import extract_phrases

    opts = options_from_env()
    print(
        f"[pipeline] phrases: method={opts.phrase_method} "
        f"n={opts.phrase_n} top={opts.phrase_top}"
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


def run_clusters() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("clusters")

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
    _stamp(
        "clusters",
        {
            "cluster_count": summary.get("cluster_count"),
            "paper_count": summary.get("paper_count"),
            "graph_summary": str(opts.workdir / "clusters" / "graph_summary.json"),
        },
    )
    print(f"[pipeline] clusters: {summary.get('cluster_count')} clusters")
    return summary


def run_clean() -> Dict[str, Any]:
    return run_placeholder("clean")


def run_encyclopedia() -> Dict[str, Any]:
    return run_placeholder("encyclopedia")


def run_kg() -> Dict[str, Any]:
    return run_placeholder("kg")


STEP_ACTIONS = {
    "query": run_query,
    "documents": run_documents,
    "corpus": run_corpus,
    "phrases": run_phrases,
    "pdfs": run_pdfs,
    "clusters": run_clusters,
    "clean": run_clean,
    "encyclopedia": run_encyclopedia,
    "kg": run_kg,
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
    if step in ("query", "corpus"):
        return (workdir / "bagit.txt").is_file()
    if step == "phrases":
        return (workdir / "phrases" / "index.json").is_file()
    if step == "clusters":
        return (workdir / "clusters" / "graph_summary.json").is_file()
    return True
