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
    DEFAULT_KG_MAX_ISLAND,
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

_SUBCOMMANDS = frozenset({"list", "graph", "status", "forget", "run", "help"})

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
        "--kg-max-island",
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
        if tok in ("--always", "-a"):
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
    limit = getattr(args, "limit", None)
    if from_mode == "query" and limit is None:
        limit = DEFAULT_LIMIT
    repository = getattr(args, "repository", None)
    if from_mode == "query" and not repository:
        repository = DEFAULT_REPOSITORY
    return PipelineOptions(
        workdir=Path(args.workdir),
        from_mode=from_mode,
        query=query,
        source=source,
        limit=limit if from_mode == "query" else None,
        repository=repository if from_mode == "query" else None,
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
        kg_max_island=getattr(args, "kg_max_island", DEFAULT_KG_MAX_ISLAND),
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
    if from_mode == "query" and not get_query():
        print(
            'Live search requires --query "…" '
            "(plus optional --limit / --repository). "
            "Omit --query/--source to use an existing corpus under --workdir.",
            file=sys.stderr,
        )
        return 2
    if from_mode == "documents" and not get_source():
        print("Document start requires --source <path>.", file=sys.stderr)
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

    # --- query (required when using live search) ---
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help='Live search string (required for search path), e.g. "amoc AND insolation"',
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
        help=f"Repository adapter for --query (default: {DEFAULT_REPOSITORY})",
    )

    # --- documents ---
    parser.add_argument(
        "--source",
        "-s",
        default=None,
        help="Local documents path/glob (implies documents → corpus)",
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

    # --- encyclopedia / kg (stubs) ---
    parser.add_argument(
        "--encyclopedia-lang",
        default=DEFAULT_ENCYCLOPEDIA_LANG,
        help=f"Wikipedia language code (default: {DEFAULT_ENCYCLOPEDIA_LANG})",
    )
    parser.add_argument(
        "--kg-max-island",
        type=int,
        default=DEFAULT_KG_MAX_ISLAND,
        help=f"Max island size to surface as FP hints (default: {DEFAULT_KG_MAX_ISLAND})",
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
  pipeline --workdir corpora/amoc --query "amoc AND insolation" --limit 50 --target clusters
  pipeline --workdir corpora/amoc --source 'wg2/chapter[2-6]' --target clusters
  pipeline --workdir corpora/amoc --target clusters
  pipeline --workdir corpora/amoc --query "AMOC AND India" \\
      --phrase-method tfidf --phrase-n 3 --cluster-resolution 0.8 --target clusters
  pipeline list
  pipeline graph --from query
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
