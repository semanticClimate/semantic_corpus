#!/usr/bin/env python3
"""Run cluster-review Steps 0–2 from the command line (no Streamlit).

Default path contract matches docs/cluster_filtering_workflow.md §12
(AMOC AND India). Default log level is ``--warn``.

  ./venv/bin/python examples/cluster_review/run_steps_0_2.py --limit 3
  ./venv/bin/python examples/cluster_review/run_steps_0_2.py --info --limit 3
  ./venv/bin/python examples/cluster_review/run_steps_0_2.py --debug --pause --limit 3

Requires: network for Step 0; ``scikit-learn`` for Step 2 TF-IDF (default).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.cluster_review import (
    DEFAULT_METHOD,
    DEFAULT_N,
    clear_all_caches,
    create_corpus_from_query,
    extract_phrases,
    load_bagit_corpus,
)
from semantic_corpus.core.exceptions import CorpusError, RepositoryError
from semantic_corpus.utils import get_project_temp_dir


DEFAULT_QUERY = "AMOC AND India"
DEFAULT_QUERY_NAME = "amoc_india_2026"

# Short step names (1–3 words) shown to the user
STEP_NAMES = {
    0: "Query download",
    1: "Load corpus",
    2: "TF-IDF phrases",
}

LOG = logging.getLogger("cluster_review.steps_0_2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cluster-review Steps 0–2 CLI (query → BAGIT → phrases)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    verb = parser.add_mutually_exclusive_group()
    verb.add_argument(
        "--error",
        action="store_const",
        const="error",
        dest="log_level",
        help="Only errors",
    )
    verb.add_argument(
        "--warn",
        action="store_const",
        const="warn",
        dest="log_level",
        help="Warnings + errors + one line per step (default)",
    )
    verb.add_argument(
        "--info",
        action="store_const",
        const="info",
        dest="log_level",
        help="Short progress (≤5 lines per step)",
    )
    verb.add_argument(
        "--debug",
        action="store_const",
        const="debug",
        dest="log_level",
        help="Verbose: titles, path samples, JSON",
    )
    parser.set_defaults(log_level="warn")
    parser.add_argument(
        "--pause",
        action="store_true",
        help="Wait for Enter after each step",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Repository query (default: {DEFAULT_QUERY!r})",
    )
    parser.add_argument(
        "--query-name",
        default=DEFAULT_QUERY_NAME,
        help=f"Run / corpus name (default: {DEFAULT_QUERY_NAME})",
    )
    parser.add_argument(
        "--repository",
        default="europe_pmc",
        help="Repository key or comma-separated list (default: europe_pmc)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max papers to download (default: 50)",
    )
    parser.add_argument(
        "--formats",
        default="xml",
        help="Comma-separated formats (default: xml)",
    )
    parser.add_argument(
        "--query-dir",
        type=str,
        help="Step 0 harvest dir (default: temp/queries/<query-name>)",
    )
    parser.add_argument(
        "--corpus-dir",
        type=str,
        help="Active corpus root (default: corpora/<query-name>)",
    )
    parser.add_argument(
        "--from-step",
        type=int,
        choices=(0, 1, 2),
        default=0,
        help="Start at this step (0=harvest, 1=load bag, 2=YAKE only)",
    )
    parser.add_argument(
        "--to-step",
        type=int,
        choices=(0, 1, 2),
        default=2,
        help="Stop after this step (default: 2)",
    )
    parser.add_argument(
        "--yake-n",
        type=int,
        default=DEFAULT_N,
        help=f"YAKE max n-gram (default: {DEFAULT_N})",
    )
    parser.add_argument(
        "--phrase-method",
        choices=["tfidf", "yake"],
        default=DEFAULT_METHOD,
        help=f"Step 2 extractor (default: {DEFAULT_METHOD})",
    )
    parser.add_argument(
        "--yake-top",
        type=int,
        default=15,
        help="Phrases per paper (default: 15)",
    )
    parser.add_argument(
        "--clear-phrases",
        action="store_true",
        help="Delete <corpus>/phrases/ before Step 2",
    )
    parser.add_argument(
        "--force-yake",
        action="store_true",
        help="Re-extract phrases even if phrase cache exists",
    )
    parser.add_argument(
        "--yake-title-abstract-only",
        action="store_true",
        help=(
            "Legacy: phrases from metadata title+abstract only (skip XML body). "
            "Default indexes XML body only (no front matter / references)."
        ),
    )
    parser.add_argument(
        "--json-summary",
        type=str,
        help="Write a combined JSON summary to this path",
    )
    return parser.parse_args()


_LEVEL_MAP = {
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


# Third-party loggers that spam INFO during BAGIT manifest updates, HTTP, etc.
_NOISY_LOGGERS = (
    "bagit",
    "urllib3",
    "requests",
    "charset_normalizer",
)


def configure_logging(log_level: str) -> None:
    """Send our step messages to stderr; keep bagit/etc quiet unless --debug."""
    level = _LEVEL_MAP.get(log_level, logging.WARNING)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    # Root stays at WARNING so libraries don't flood --warn/--info.
    # Only --debug opens the firehose for bagit manifest lines, etc.
    root.setLevel(logging.DEBUG if log_level == "debug" else logging.WARNING)

    LOG.setLevel(level)
    LOG.propagate = True

    library_level = logging.DEBUG if log_level == "debug" else logging.WARNING
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(library_level)


def _step_label(step: int) -> str:
    return f"Step {step} — {STEP_NAMES[step]}"


def _banner(step: int) -> None:
    """INFO+ only — counts toward the ≤5-line budget."""
    LOG.info("%s", _step_label(step))


def _step_result(step: int, msg: str) -> None:
    """One completion line: WARNING at --warn; INFO at --info/--debug (no duplicate)."""
    label = _step_label(step)
    if LOG.isEnabledFor(logging.INFO):
        LOG.info("  %s", msg)
    else:
        LOG.warning("%s: %s", label, msg)


def _pause_if_requested(enabled: bool, step: int) -> None:
    if not enabled:
        return
    try:
        input(f">>> {_step_label(step)} done. Enter to continue (Ctrl-C abort)… ")
    except EOFError:
        LOG.warning("No TTY for --pause; continuing.")


def _list_sample_files(directory: Path, pattern: str, limit: int = 5) -> List[str]:
    if not directory.is_dir():
        return []
    paths = sorted(directory.glob(pattern))
    names = [p.name for p in paths[:limit]]
    if len(paths) > limit:
        names.append(f"... (+{len(paths) - limit} more)")
    return names


def run_step0(
    *,
    query: str,
    query_name: str,
    query_dir: Path,
    corpus_dir: Path,
    repositories: list,
    limit: int,
    formats: list,
    pause: bool,
) -> Dict[str, Any]:
    _banner(0)
    LOG.info("  query=%r  limit=%s  formats=%s", query, limit, formats)
    LOG.info("  → %s", corpus_dir)
    LOG.debug("  query_dir=%s  repos=%s", query_dir, repositories)

    summary = create_corpus_from_query(
        query_string=query,
        query_name=query_name,
        query_dir=query_dir,
        repositories=repositories,
        limit=limit,
        formats=formats,
        corpus_dir=corpus_dir,
        create_bagit=True,
    )
    # IDs already printed (wrapped) by run_repository_search during download
    _step_result(
        0,
        f"{summary.get('downloaded_count')} downloaded → "
        f"{summary.get('bagit_paper_count')} papers in {corpus_dir}",
    )
    LOG.debug(
        "  summary=%s",
        {k: v for k, v in summary.items() if k not in ("rows", "bagit_paper_ids")},
    )
    LOG.debug(
        "  xml samples: %s",
        _list_sample_files(query_dir, "*.xml"),
    )
    if LOG.isEnabledFor(logging.DEBUG):
        for row in (summary.get("rows") or [])[:10]:
            LOG.debug(
                "    %s — %s",
                row.get("paper_id"),
                (row.get("title") or "")[:100],
            )

    _pause_if_requested(pause, 0)
    return summary


def run_step1(
    *,
    corpus_dir: Path,
    query_name: str,
    query: str,
    pause: bool,
) -> Dict[str, Any]:
    _banner(1)
    LOG.info("  corpus=%s", corpus_dir)

    summary = load_bagit_corpus(
        corpus_dir,
        query_name=query_name,
        query_string=query,
    )
    _step_result(1, f"{summary.get('paper_count')} papers from {corpus_dir}")
    LOG.debug(
        "  summary=%s",
        {
            k: v
            for k, v in summary.items()
            if k not in ("rows", "papers", "paper_ids")
        },
    )
    if LOG.isEnabledFor(logging.DEBUG):
        for paper in (summary.get("papers") or [])[:10]:
            LOG.debug(
                "    %s — %s",
                paper.get("paper_id"),
                (paper.get("title") or "")[:100],
            )

    _pause_if_requested(pause, 1)
    return summary


def run_step2(
    *,
    corpus_dir: Path,
    n: int,
    top: int,
    clear_phrases: bool,
    force: bool,
    pause: bool,
    method: str = DEFAULT_METHOD,
    include_xml_body: bool = True,
    include_front_matter: bool = False,
) -> Dict[str, Any]:
    _banner(2)
    LOG.info(
        "  corpus=%s  method=%s  n=%s  top=%s  xml_body=%s  front_matter=%s",
        corpus_dir,
        method,
        n,
        top,
        include_xml_body,
        include_front_matter,
    )
    if clear_phrases:
        cleared = clear_all_caches(corpus_dir)
        LOG.info("  cleared %s cache files", cleared["deleted_count"])
        LOG.debug("  cleared under %s", cleared["phrases_dir"])

    def _progress(i: int, total: int, paper_id: str, elapsed: float) -> None:
        # Per-paper lines only at DEBUG (would blow the INFO 5-line budget)
        LOG.debug("  [%s/%s] %s (%.3fs)", i, total, paper_id, elapsed)

    summary = extract_phrases(
        corpus_dir,
        method=method,
        n=n,
        top=top,
        use_cache=not force,
        force=force,
        progress_callback=_progress,
        include_xml_body=include_xml_body,
        include_front_matter=include_front_matter,
    )
    _step_result(
        2,
        f"{summary.get('unique_phrases')} unique phrases "
        f"({summary.get('paper_count')} papers) → {summary.get('phrases_dir')}",
    )
    LOG.debug(
        "  summary=%s",
        {k: v for k, v in summary.items() if k not in ("papers", "paper_ids")},
    )
    if LOG.isEnabledFor(logging.DEBUG):
        for paper in (summary.get("papers") or [])[:10]:
            top_phrases = ", ".join(
                p["phrase"] for p in (paper.get("phrases") or [])[:5]
            )
            LOG.debug(
                "    %s [%s]: %s",
                paper["paper_id"],
                paper["source"],
                top_phrases,
            )

    _pause_if_requested(pause, 2)
    return summary


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    if args.from_step > args.to_step:
        LOG.error("--from-step cannot be greater than --to-step")
        return 2

    query_name = args.query_name.strip() or DEFAULT_QUERY_NAME
    query_dir = (
        Path(args.query_dir)
        if args.query_dir
        else Path(get_project_temp_dir(), "queries", query_name)
    )
    corpus_dir = (
        Path(args.corpus_dir) if args.corpus_dir else Path("corpora", query_name)
    )
    repositories = [r.strip() for r in args.repository.split(",") if r.strip()]
    formats = [f.strip() for f in args.formats.split(",") if f.strip()] or ["xml"]

    LOG.info(
        "Steps 0–2  [%s]  corpus=%s  steps=%s..%s",
        args.log_level.upper(),
        corpus_dir,
        args.from_step,
        args.to_step,
    )
    LOG.debug("  query_dir=%s  pause=%s", query_dir, args.pause)

    combined: Dict[str, Any] = {
        "query": args.query,
        "query_name": query_name,
        "query_dir": str(query_dir.resolve()),
        "corpus_dir": str(corpus_dir.resolve()),
        "from_step": args.from_step,
        "to_step": args.to_step,
    }

    try:
        if args.from_step <= 0 <= args.to_step:
            combined["step0"] = run_step0(
                query=args.query,
                query_name=query_name,
                query_dir=query_dir,
                corpus_dir=corpus_dir,
                repositories=repositories,
                limit=args.limit,
                formats=formats,
                pause=args.pause,
            )

        if args.from_step <= 1 <= args.to_step:
            if not corpus_dir.exists():
                raise CorpusError(
                    f"Corpus not found: {corpus_dir}. Run Step 0 first "
                    "(omit --from-step, or use --from-step 0)."
                )
            combined["step1"] = run_step1(
                corpus_dir=corpus_dir,
                query_name=query_name,
                query=args.query,
                pause=args.pause,
            )

        if args.from_step <= 2 <= args.to_step:
            if not corpus_dir.exists():
                raise CorpusError(
                    f"Corpus not found: {corpus_dir}. Run Steps 0–1 first."
                )
            title_abs_only = args.yake_title_abstract_only
            combined["step2"] = run_step2(
                corpus_dir=corpus_dir,
                n=args.yake_n,
                top=args.yake_top,
                clear_phrases=args.clear_phrases,
                force=args.force_yake,
                pause=args.pause,
                method=args.phrase_method,
                # Default: body only. Legacy flag flips to title+abstract only.
                include_xml_body=not title_abs_only,
                include_front_matter=title_abs_only,
            )
    except (CorpusError, RepositoryError) as exc:
        message = getattr(exc, "message", None) or str(exc)
        LOG.error("%s", message)
        return 1
    except KeyboardInterrupt:
        LOG.error("Interrupted.")
        return 130
    except Exception as exc:  # noqa: BLE001
        LOG.error("%s", exc)
        if args.log_level == "debug":
            LOG.exception("debug traceback:")
        return 1

    done_path = (
        combined["step2"].get("phrases_dir")
        if "step2" in combined
        else str(corpus_dir)
    )
    if LOG.isEnabledFor(logging.INFO):
        LOG.info("Done: corpus=%s", corpus_dir)
        if "step2" in combined:
            LOG.info("  phrases=%s", combined["step2"].get("phrases_dir"))
    else:
        LOG.warning("Done: %s", done_path)

    if args.json_summary:
        out = Path(args.json_summary)
        out.parent.mkdir(parents=True, exist_ok=True)
        serializable: Dict[str, Any] = {
            k: v
            for k, v in combined.items()
            if k not in ("step0", "step1", "step2")
        }
        for key in ("step0", "step1", "step2"):
            if key not in combined:
                continue
            block = combined[key]
            serializable[key] = {
                kk: vv
                for kk, vv in block.items()
                if kk not in ("rows", "papers", "paper_ids", "bagit_paper_ids")
            }
        out.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        LOG.warning("Wrote summary: %s", out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
