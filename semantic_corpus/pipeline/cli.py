"""Command-line entry for the symbolic pipeline (``pipeline``).

Examples::

    pipeline --workdir corpora/amoc --query "amoc AND insolation" --limit 50 --target clusters
    pipeline --workdir corpora/amoc --source wg2/chapter[2-6] --target clusters
    pipeline --workdir corpora/amoc --target clusters
    pipeline --workdir corpora/amoc --query "…" --phrase-method tfidf --cluster-resolution 0.8 --target clusters
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from semantic_corpus.pipeline.config import (
    DEFAULT_CLUSTER_ALGORITHM,
    DEFAULT_CLUSTER_RESOLUTION,
    DEFAULT_ENCYCLOPEDIA_LANG,
    DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES,
    DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT,
    DEFAULT_ENCYCLOPEDIA_MIN_SCORE,
    DEFAULT_ENCYCLOPEDIA_SOURCE,
    DEFAULT_KG_LINKS,
    DEFAULT_KG_OPEN,
    DEFAULT_WRITE_KG,
    ENCYCLOPEDIA_SOURCE_CHOICES,
    DEFAULT_KG_MAX_ISLAND,
    DEFAULT_KG_MAX_TERMS,
    DEFAULT_KG_MIN_PAPER_COUNT,
    DEFAULT_LIMIT,
    DEFAULT_PHRASE_METHOD,
    DEFAULT_PHRASE_N,
    DEFAULT_PHRASE_TOP,
    DEFAULT_REPOSITORY,
    DEFAULT_WORKDIR,
    PipelineOptions,
    apply_env,
    get_from_mode,
    get_limit,
    get_query,
    get_source,
    get_workdir,
    infer_from_mode,
    options_from_env,
)
from semantic_corpus.pipeline.placeholders import (
    pipeline_dir,
    stamp_exists,
    stamp_path,
)
from semantic_corpus.pipeline.steps import (
    FROM_MODES,
    STEP_DOCS,
    STEP_NAMES,
    deps_for,
    doit_basename,
    graph_text,
    required_steps,
)

_SUBCOMMANDS = frozenset(
    {"list", "graph", "status", "forget", "run", "encyclopedia", "kg", "help"}
)

_OPTS_WITH_VALUE = frozenset(
    {
        "--workdir",
        "-w",
        "--query",
        "-q",
        "--source",
        "-s",
        "--limit",
        "-n",
        "--repository",
        "--target",
        "-t",
        "--from",
        "--phrase-method",
        "--phrase-n",
        "--phrase-top",
        "--cluster-resolution",
        "--cluster-algorithm",
        "--encyclopedia-lang",
        "--max-entries",
        "--min-score",
        "--min-paper-count",
        "--encyclopedia-from",
        "--kg-max-island",
        "--kg-max-terms",
        "--kg-min-paper-count",
        "--kg-links",
    }
)


def _load_dodo():
    import semantic_corpus.pipeline.dodo as dodo

    return importlib.reload(dodo)


def _doit_main(doit_args: List[str]) -> int:
    try:
        from doit.cmd_base import ModuleTaskLoader
        from doit.doit_cmd import DoitMain
    except ImportError:
        print(
            "doit is required for the pipeline runner.\n"
            "Install with: pip install 'semantic_corpus[cluster_review]'\n"
            "  (or: pip install doit)",
            file=sys.stderr,
        )
        return 2

    dodo = _load_dodo()
    return DoitMain(ModuleTaskLoader(dodo)).run(doit_args)


def _normalize_argv(argv: List[str]) -> List[str]:
    if not argv:
        return ["list"]

    leading_opts: List[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in _OPTS_WITH_VALUE:
            leading_opts.extend(argv[i : i + 2])
            i += 2
            continue
        if tok.startswith("--") and "=" in tok:
            leading_opts.append(tok)
            i += 1
            continue
        if tok in (
            "--always",
            "-a",
            "--open",
            "--no-open",
            "--kg",
            "--no-kg",
        ):
            leading_opts.append(tok)
            i += 1
            continue
        break

    rest = argv[i:]
    if not rest:
        return ["run", *leading_opts]

    head, tail = rest[0], rest[1:]
    if head in _SUBCOMMANDS:
        return [head, *leading_opts, *tail]
    if head in STEP_NAMES:
        return ["run", *leading_opts, "--target", head, *tail]
    return argv


def _options_from_args(args: argparse.Namespace) -> PipelineOptions:
    query = getattr(args, "query", None)
    source = getattr(args, "source", None)
    explicit = getattr(args, "from_mode", None)
    from_mode = explicit if explicit else infer_from_mode(query, source)
    # Remote-search defaults only apply when --query is set.
    limit = getattr(args, "limit", None)
    repository = getattr(args, "repository", None)
    if query:
        if limit is None:
            limit = DEFAULT_LIMIT
        if not repository:
            repository = DEFAULT_REPOSITORY
    return PipelineOptions(
        workdir=Path(args.workdir),
        from_mode=from_mode,
        query=query,
        source=source,
        limit=limit if query else None,
        repository=repository if query else None,
        phrase_method=getattr(args, "phrase_method", DEFAULT_PHRASE_METHOD),
        phrase_n=getattr(args, "phrase_n", DEFAULT_PHRASE_N),
        phrase_top=getattr(args, "phrase_top", DEFAULT_PHRASE_TOP),
        cluster_resolution=getattr(
            args, "cluster_resolution", DEFAULT_CLUSTER_RESOLUTION
        ),
        cluster_algorithm=getattr(
            args, "cluster_algorithm", DEFAULT_CLUSTER_ALGORITHM
        ),
        encyclopedia_lang=getattr(
            args, "encyclopedia_lang", DEFAULT_ENCYCLOPEDIA_LANG
        ),
        max_entries=getattr(
            args, "max_entries", DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES
        ),
        min_score=getattr(args, "min_score", DEFAULT_ENCYCLOPEDIA_MIN_SCORE),
        min_paper_count=getattr(args, "min_paper_count", DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT),
        encyclopedia_source=getattr(
            args, "encyclopedia_source", DEFAULT_ENCYCLOPEDIA_SOURCE
        ),
        write_kg=bool(getattr(args, "write_kg", DEFAULT_WRITE_KG)),
        kg_max_island=getattr(args, "kg_max_island", DEFAULT_KG_MAX_ISLAND),
        kg_max_terms=getattr(args, "kg_max_terms", DEFAULT_KG_MAX_TERMS),
        kg_min_paper_count=getattr(
            args, "kg_min_paper_count", DEFAULT_KG_MIN_PAPER_COUNT
        ),
        kg_links=getattr(args, "kg_links", DEFAULT_KG_LINKS),
        kg_open=bool(getattr(args, "open", DEFAULT_KG_OPEN)),
    )


def _resolve_targets(args: argparse.Namespace) -> List[str]:
    targets = list(getattr(args, "targets", None) or [])
    positional = list(getattr(args, "positional_targets", None) or [])
    return targets + positional


def cmd_list(_: argparse.Namespace) -> int:
    from_mode = get_from_mode()
    print(f"pipeline steps (start={from_mode}):")
    for name in STEP_NAMES:
        deps = deps_for(name, from_mode)
        dep_s = f"  ← {', '.join(deps)}" if deps else ""
        print(f"  {name:14s}  {STEP_DOCS[name]}{dep_s}")
    return 0


def cmd_graph(_: argparse.Namespace) -> int:
    print(graph_text(get_from_mode()))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    workdir = get_workdir()
    from_mode = get_from_mode()
    opts = options_from_env()
    print(f"workdir: {workdir}")
    print(f"start:   {from_mode}")
    if get_query():
        print(
            f"query:   {get_query()!r}  limit={get_limit()}  "
            f"repository={opts.repository!r}"
        )
    if get_source():
        print(f"source:  {get_source()!r}")
    print(
        f"phrases: method={opts.phrase_method} n={opts.phrase_n} top={opts.phrase_top}"
    )
    print(
        f"clusters: algorithm={opts.cluster_algorithm} "
        f"resolution={opts.cluster_resolution}"
    )
    print(f"stamps:  {pipeline_dir(workdir)}")
    for name in STEP_NAMES:
        mark = "done" if stamp_exists(name, workdir) else "----"
        print(f"  [{mark}] {name}")
    targets = _resolve_targets(args)
    if targets:
        plan = required_steps(targets, from_mode)
        print(f"\nto ensure {targets} would run (or skip): {plan}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args) or ["clusters"]
    unknown = [t for t in targets if t not in STEP_NAMES]
    if unknown:
        print(
            f"Unknown --target: {unknown}. Choose from: {STEP_NAMES}",
            file=sys.stderr,
        )
        return 2

    from_mode = get_from_mode()
    if from_mode == "collect" and not get_query() and not get_source():
        print(
            "Collect requires --query \"…\" (EPMC/other remotes; "
            "optional --limit / --repository) or --source <path> "
            "(static documents). "
            "Omit both to use an existing corpus under --workdir.",
            file=sys.stderr,
        )
        return 2

    opts = options_from_env()
    plan = required_steps(targets, from_mode)
    bits = [f"start={from_mode}", f"workdir={get_workdir()}"]
    if get_query():
        bits.append(f"query={get_query()!r}")
        bits.append(f"limit={get_limit()}")
        bits.append(f"repository={opts.repository!r}")
    if get_source():
        bits.append(f"source={get_source()!r}")
    print(f"[pipeline] {' '.join(bits)}")
    print(f"[pipeline] ensure {targets} → plan {plan}")

    doit_args: List[str] = ["run"]
    if args.always:
        doit_args.append("--always-execute")
    doit_args.extend(doit_basename(t) for t in targets)
    return _doit_main(doit_args)


def cmd_encyclopedia(args: argparse.Namespace) -> int:
    """Rebuild phrases → encyclopedia (Wikipedia + disambiguation + HTML).

    Bypasses the full doit graph so ``--encyclopedia-from phrases`` does not
    require remaking clusters. Optionally re-extracts phrases first.
    """
    from semantic_corpus.cluster_review.encyclopedia import build_encyclopedia
    from semantic_corpus.cluster_review.step2 import extract_phrases
    from semantic_corpus.pipeline.placeholders import write_stamp

    opts = options_from_env()
    workdir = opts.workdir
    if not workdir.is_dir():
        print(f"workdir not found: {workdir}", file=sys.stderr)
        return 2

    source = getattr(args, "encyclopedia_source", None) or opts.encyclopedia_source
    if source == "auto":
        source = "phrases"
    force = bool(getattr(args, "always", False) or getattr(args, "force", False))
    rebuild_phrases = bool(getattr(args, "rebuild_phrases", False))
    no_html = bool(getattr(args, "no_html", False))
    no_disambiguate = bool(getattr(args, "no_disambiguate", False))

    print(
        f"[pipeline] encyclopedia: workdir={workdir} from={source} "
        f"max_entries={opts.max_entries} min_paper_count={opts.min_paper_count} "
        f"rebuild_phrases={rebuild_phrases} force={force}"
    )

    if rebuild_phrases or not (workdir / "phrases" / "index.json").is_file():
        print(
            f"[pipeline] phrases: method={opts.phrase_method} "
            f"n={opts.phrase_n} top={opts.phrase_top} force={rebuild_phrases or force}"
        )
        phrase_summary = extract_phrases(
            workdir,
            method=opts.phrase_method,
            n=opts.phrase_n,
            top=opts.phrase_top,
            use_cache=True,
            force=rebuild_phrases or force,
        )
        write_stamp(
            "phrases",
            workdir,
            {
                "status": "ok",
                "paper_count": phrase_summary.get("paper_count"),
                "index": str(workdir / "phrases" / "index.json"),
            },
        )
        print(
            f"[pipeline] phrases: done "
            f"({phrase_summary.get('paper_count')} papers, "
            f"{phrase_summary.get('unique_phrases')} unique)"
        )

    if not (workdir / "phrases" / "phrases_terms.csv").is_file() and source == "phrases":
        print(
            f"missing phrases_terms.csv under {workdir / 'phrases'}; "
            "run with --rebuild-phrases",
            file=sys.stderr,
        )
        return 2

    doc = build_encyclopedia(
        workdir,
        lang=opts.encyclopedia_lang,
        max_entries=int(opts.max_entries),
        min_score=float(opts.min_score),
        min_paper_count=int(opts.min_paper_count),
        source=source,
        force=force,
        write_html=not no_html,
        fetch_html_descriptions=not no_html,
        disambiguate=not no_disambiguate,
        html_title=getattr(args, "html_title", None)
        or f"Encyclopedia ({workdir.name})",
    )
    counts = doc.get("counts") or {}
    write_stamp(
        "encyclopedia",
        workdir,
        {
            "status": "ok",
            "entries_path": doc.get("entries_path"),
            "html_path": doc.get("html_path"),
            "selected": counts.get("selected"),
            "resolved": counts.get("resolved"),
            "ambiguous": counts.get("ambiguous"),
            "missing": counts.get("missing"),
            "error": counts.get("error"),
            "disambiguated": counts.get("disambiguated"),
            "phrase_source": (doc.get("params") or {}).get("phrase_source"),
        },
    )
    print(
        f"[pipeline] encyclopedia: selected={counts.get('selected')} "
        f"resolved={counts.get('resolved')} ambiguous={counts.get('ambiguous')} "
        f"missing={counts.get('missing')} disambiguated={counts.get('disambiguated')} "
        f"error={counts.get('error')}"
    )
    if doc.get("entries_path"):
        print(f"[pipeline] entries: {doc['entries_path']}")
    if doc.get("html_path"):
        print(f"[pipeline] html:    {doc['html_path']}")
    selected = int(counts.get("selected") or 0)
    errors = int(counts.get("error") or 0)
    if selected and errors == selected:
        return 1
    return 0


def cmd_kg(args: argparse.Namespace) -> int:
    """Rebuild display KG HTML (helper; not a doit step).

    Prefer ``pipeline --target clusters --kg`` (plain) or
    ``pipeline --target encyclopedia --kg`` (annotated).
    """
    from semantic_corpus.cluster_review.kg import build_kg

    opts = options_from_env()
    workdir = opts.workdir
    if not (workdir / "clusters" / "clusters.json").is_file():
        print(
            f"missing clusters/clusters.json under {workdir}; "
            "run: pipeline run --workdir … --target clusters --kg",
            file=sys.stderr,
        )
        return 2

    links = opts.kg_link_list()
    enc = workdir / "encyclopedia" / "entries.json"
    if enc.is_file() and "wikipedia" not in links and "wikidata" not in links:
        links = tuple(list(links) + ["wikipedia"])
    open_browser = bool(getattr(args, "open", opts.kg_open))
    stage = "encyclopedia" if enc.is_file() else "clusters"
    print(
        f"[pipeline] kg (rebuild/{stage}): workdir={workdir} "
        f"links={','.join(links)} "
        f"min_paper_count={opts.kg_min_paper_count} max_terms={opts.kg_max_terms} "
        f"max_island={opts.kg_max_island} open={open_browser}"
    )
    summary = build_kg(
        workdir,
        kg_links=links,
        max_island=int(opts.kg_max_island),
        min_paper_count=int(opts.kg_min_paper_count),
        max_terms=int(opts.kg_max_terms),
        write_html=True,
        open_browser=open_browser,
        title=getattr(args, "html_title", None)
        or f"Knowledge graph ({workdir.name})",
    )
    counts = summary.get("counts") or {}
    print(
        f"[pipeline] kg: nodes={counts.get('nodes')} edges={counts.get('edges')} "
        f"papers={counts.get('papers')} terms={counts.get('terms')} "
        f"islands={counts.get('islands')} "
        f"(filter n_papers>={opts.kg_min_paper_count}, max_terms={opts.kg_max_terms})"
    )
    if summary.get("html_path"):
        print(f"[pipeline] html: {summary['html_path']}")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args)
    if not targets:
        print(
            "usage: pipeline forget --workdir DIR --target <step> ...",
            file=sys.stderr,
        )
        return 2
    unknown = [t for t in targets if t not in STEP_NAMES]
    if unknown:
        print(
            f"Unknown step(s): {unknown}. Choose from: {STEP_NAMES}",
            file=sys.stderr,
        )
        return 2
    workdir = get_workdir()
    for step in targets:
        path = stamp_path(step, workdir)
        if path.is_file():
            path.unlink()
            print(f"[pipeline] removed stamp {path}")
    return _doit_main(["forget", *(doit_basename(t) for t in targets)])


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    # --- always ---
    parser.add_argument(
        "--workdir",
        "-w",
        type=Path,
        default=Path(DEFAULT_WORKDIR),
        help=f"Corpus root (default: {DEFAULT_WORKDIR})",
    )
    parser.add_argument(
        "--target",
        "-t",
        action="append",
        dest="targets",
        metavar="STEP",
        choices=STEP_NAMES,
        help="Goal step to ensure (repeatable). Default for run: clusters",
    )

    # --- collect options (mutually exclusive) ---
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help=(
            'Collect via remote search (EPMC / --repository), '
            'e.g. "amoc AND insolation"'
        ),
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help=f"Max hits for --query (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--repository",
        default=None,
        help=f"Remote adapter for --query (default: {DEFAULT_REPOSITORY})",
    )
    parser.add_argument(
        "--source",
        "-s",
        default=None,
        help="Collect from static documents (path/glob); alternative to --query",
    )

    # --- phrases ---
    parser.add_argument(
        "--phrase-method",
        default=DEFAULT_PHRASE_METHOD,
        choices=("tfidf", "yake"),
        help=f"Keyphrase method (default: {DEFAULT_PHRASE_METHOD})",
    )
    parser.add_argument(
        "--phrase-n",
        type=int,
        default=DEFAULT_PHRASE_N,
        help=f"n-gram size for phrases (default: {DEFAULT_PHRASE_N})",
    )
    parser.add_argument(
        "--phrase-top",
        type=int,
        default=DEFAULT_PHRASE_TOP,
        help=f"Top-k phrases per paper (default: {DEFAULT_PHRASE_TOP})",
    )

    # --- clusters ---
    parser.add_argument(
        "--cluster-algorithm",
        default=DEFAULT_CLUSTER_ALGORITHM,
        help=f"Community algorithm (default: {DEFAULT_CLUSTER_ALGORITHM})",
    )
    parser.add_argument(
        "--cluster-resolution",
        type=float,
        default=DEFAULT_CLUSTER_RESOLUTION,
        help=f"Louvain resolution (default: {DEFAULT_CLUSTER_RESOLUTION})",
    )

    # --- encyclopedia / kg (stubs; see docs/pipeline_next_encyclopedia_kg.md) ---
    parser.add_argument(
        "--encyclopedia-lang",
        default=DEFAULT_ENCYCLOPEDIA_LANG,
        help=f"Wikipedia language code (default: {DEFAULT_ENCYCLOPEDIA_LANG})",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES,
        metavar="N",
        help=(
            "Max encyclopedia phrases to resolve "
            f"(default: {DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES})"
        ),
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_ENCYCLOPEDIA_MIN_SCORE,
        help=(
            "Minimum phrase/cluster score to include "
            f"(default: {DEFAULT_ENCYCLOPEDIA_MIN_SCORE})"
        ),
    )
    parser.add_argument(
        "--min-paper-count",
        type=int,
        default=DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT,
        metavar="N",
        help=(
            "Minimum n_papers from phrases_terms.csv "
            f"(default: {DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT})"
        ),
    )
    parser.add_argument(
        "--encyclopedia-from",
        dest="encyclopedia_source",
        choices=ENCYCLOPEDIA_SOURCE_CHOICES,
        default=DEFAULT_ENCYCLOPEDIA_SOURCE,
        help=(
            "Phrase pool: auto (clusters if present), clusters, or phrases "
            "(phrases_terms.csv when present) "
            f"(default: {DEFAULT_ENCYCLOPEDIA_SOURCE})"
        ),
    )
    parser.add_argument(
        "--kg",
        dest="write_kg",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_WRITE_KG,
        help=(
            "After clusters or encyclopedia, also write/open the display KG "
            f"(default: {'on' if DEFAULT_WRITE_KG else 'off'}; cheap view assembly, "
            "not a pipeline step — two graphs: plain after clusters, annotated after encyclopedia)"
        ),
    )
    parser.add_argument(
        "--kg-links",
        default=DEFAULT_KG_LINKS,
        metavar="SOURCES",
        help=(
            "Comma-separated kg edge sources for encyclopedia-stage KG: "
            f"clusters,wikipedia,wikidata (default: {DEFAULT_KG_LINKS}; "
            "clusters-stage KG always uses clusters only)"
        ),
    )
    parser.add_argument(
        "--kg-max-island",
        type=int,
        default=DEFAULT_KG_MAX_ISLAND,
        help=f"Max island size to surface as FP hints (default: {DEFAULT_KG_MAX_ISLAND})",
    )
    parser.add_argument(
        "--kg-max-terms",
        type=int,
        default=DEFAULT_KG_MAX_TERMS,
        metavar="N",
        help=(
            "Max term nodes in the KG after ranking by n_papers "
            f"(default: {DEFAULT_KG_MAX_TERMS})"
        ),
    )
    parser.add_argument(
        "--kg-min-paper-count",
        type=int,
        default=DEFAULT_KG_MIN_PAPER_COUNT,
        metavar="N",
        help=(
            "Minimum phrases_terms n_papers for a term to enter the KG "
            f"(default: {DEFAULT_KG_MIN_PAPER_COUNT})"
        ),
    )
    parser.add_argument(
        "--open",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_KG_OPEN,
        help=(
            "When writing a display KG (--kg), open knowledge_graph.html "
            f"(default: {'on' if DEFAULT_KG_OPEN else 'off'}; use --no-open to disable)"
        ),
    )

    parser.add_argument(
        "--from",
        dest="from_mode",
        choices=FROM_MODES,
        default=None,
        help="Override start mode for graph/list (else inferred from --query/--source)",
    )


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    _add_common_flags(common)

    parser = argparse.ArgumentParser(
        prog="pipeline",
        description=(
            "Symbolic corpus pipeline (placeholders). "
            "--query / --source produce a corpus at --workdir; "
            "--target names the goal step."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  pipeline --workdir corpora/amoc --query "amoc AND insolation" --target clusters
  pipeline --workdir corpora/amoc --target clusters --kg
  pipeline --workdir corpora/amoc --target encyclopedia --kg
  pipeline --workdir corpora/amoc --source 'wg2/chapter[2-6]' --target clean
  pipeline encyclopedia --workdir corpora/amoc_insolation_20 \\
      --min-paper-count 2 --max-entries 50 --force
  pipeline kg --workdir corpora/amoc_insolation_20 --kg-links clusters,wikipedia
  pipeline list
  pipeline graph --from collect
""",
    )

    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", parents=[common], help="List steps")
    p_list.set_defaults(func=cmd_list)

    p_graph = sub.add_parser(
        "graph", parents=[common], help="Print dependency edges"
    )
    p_graph.set_defaults(func=cmd_graph)

    p_status = sub.add_parser("status", parents=[common], help="Show stamp status")
    p_status.add_argument(
        "positional_targets", nargs="*", metavar="STEP", help="Optional plan targets"
    )
    p_status.set_defaults(func=cmd_status)

    p_forget = sub.add_parser("forget", parents=[common], help="Clear stamps / doit state")
    p_forget.add_argument(
        "positional_targets", nargs="*", metavar="STEP", help="Steps to forget"
    )
    p_forget.set_defaults(func=cmd_forget)

    p_run = sub.add_parser("run", parents=[common], help="Ensure --target step(s)")
    p_run.add_argument(
        "--always",
        "-a",
        action="store_true",
        help="Always execute (ignore up-to-date stamps)",
    )
    p_run.set_defaults(func=cmd_run)

    p_enc = sub.add_parser(
        "encyclopedia",
        parents=[common],
        help=(
            "Rebuild phrases → Wikipedia encyclopedia "
            "(disambiguation + HTML; no clusters required)"
        ),
    )
    p_enc.add_argument(
        "--rebuild-phrases",
        action="store_true",
        help="Force re-extract phrases before encyclopedia",
    )
    p_enc.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-resolve Wikipedia entries (ignore entry cache)",
    )
    p_enc.add_argument(
        "--always",
        "-a",
        action="store_true",
        help="Same as --force (and force phrase re-extract if --rebuild-phrases)",
    )
    p_enc.add_argument(
        "--no-html",
        action="store_true",
        help="Skip AmiEncyclopedia HTML export",
    )
    p_enc.add_argument(
        "--no-disambiguate",
        action="store_true",
        help="Skip encyclopedia package disambiguation",
    )
    p_enc.add_argument(
        "--html-title",
        default=None,
        help="Title for encyclopedia.html (default: Encyclopedia (<workdir name>))",
    )
    p_enc.set_defaults(
        func=cmd_encyclopedia,
        encyclopedia_source="phrases",
    )

    p_kg = sub.add_parser(
        "kg",
        parents=[common],
        help="Build knowledge graph after clusters (+ optional HTML display)",
    )
    p_kg.add_argument(
        "--html-title",
        default=None,
        help="Title for knowledge_graph.html",
    )
    p_kg.set_defaults(func=cmd_kg)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    normalized = _normalize_argv(raw)
    parser = build_parser()
    try:
        args = parser.parse_args(normalized)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        opts = _options_from_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    apply_env(opts)
    opts.workdir.mkdir(parents=True, exist_ok=True)

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    sys.exit(main())
