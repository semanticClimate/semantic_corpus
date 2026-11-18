"""Translate pygetpapers-style CLI args into semantic_corpus search/download.

Usage examples (quoting preserved by the shell until argparse):

  semantic_corpus --pygetpapers -q 'AMOC AND India' -k 50 -o temp/queries/amoc_india_2026 -x

  semantic_corpus --pygetpapers -- -q "AMOC AND India" -k 50 -o out -x -p

  # Paste a whole pygetpapers invocation as one string (shlex-split):
  semantic_corpus --pygetpapers 'pygetpapers -q "AMOC AND India" -k 50 -o out -x'
"""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


# Flags we understand from pygetpapers → semantic_corpus
_SUPPORTED = {
    "-q",
    "--query",
    "-k",
    "--limit",
    "-o",
    "--output",
    "-x",
    "--xml",
    "-p",
    "--pdf",
    "-n",
    "--noexecute",
    "-h",
    "--help",
}

# Common pygetpapers options we deliberately ignore (with a warning)
_IGNORED_WITH_VALUE = {
    "--config",
    "--references",
    "--citations",
    "-l",
    "--loglevel",
    "-f",
    "--logfile",
    "--api",
}
_IGNORED_FLAGS = {
    "-s",
    "--supp",
    "-z",
    "--zip",
    "-r",
    "--restart",
    "-u",
    "--update",
    "--onlyquery",
    "-c",
    "--makecsv",
    "--makehtml",
    "--synonym",
    "--save_query",
    "-v",
    "--version",
    "--sa",  # sometimes used for scientific articles
}


@dataclass
class TranslatedPygetpapers:
    """Result of translating a pygetpapers argv into semantic_corpus actions."""

    query: str
    limit: int = 100
    output: Optional[str] = None
    formats: List[str] = field(default_factory=list)
    noexecute: bool = False  # search only
    warnings: List[str] = field(default_factory=list)
    command: str = "download"  # or "search"

    def to_semantic_corpus_argv(self) -> List[str]:
        """Build argv for the native semantic_corpus search/download parsers."""
        if self.noexecute or not self.formats:
            cmd = "search"
        else:
            cmd = "download"
        argv = [cmd, "--query", self.query, "--limit", str(self.limit)]
        if self.output:
            argv.extend(["--output", self.output])
        if cmd == "download":
            argv.extend(["--formats", ",".join(self.formats)])
        argv.extend(["--repository", "europe_pmc"])
        return argv


def _tokenize_tokens(raw: Sequence[str]) -> List[str]:
    """Normalize remainder tokens; allow a single pasted command string."""
    tokens = [t for t in raw if t is not None]
    # Drop a leading bare "--" (common when users write: --pygetpapers -- -q ...)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    if len(tokens) == 1 and (
        " " in tokens[0] or tokens[0].startswith("pygetpapers")
    ):
        tokens = shlex.split(tokens[0])
    # Drop leading binary name if pasted
    if tokens and tokens[0] in ("pygetpapers", "pygetpapers.py"):
        tokens = tokens[1:]
    return tokens


def parse_pygetpapers_argv(argv: Sequence[str]) -> TranslatedPygetpapers:
    """Parse pygetpapers-style argv into a :class:`TranslatedPygetpapers`.

    Raises:
        SystemExit / ValueError: on missing query or ``--help``.
    """
    tokens = _tokenize_tokens(list(argv))
    if not tokens or tokens in (["-h"], ["--help"]):
        raise SystemExit(_help_text())

    query: Optional[str] = None
    limit = 100
    output: Optional[str] = None
    want_xml = False
    want_pdf = False
    noexecute = False
    warnings: List[str] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("-q", "--query"):
            if i + 1 >= len(tokens):
                raise ValueError(f"{tok} requires a query string")
            query = tokens[i + 1]
            i += 2
            continue
        if tok in ("-k", "--limit"):
            if i + 1 >= len(tokens):
                raise ValueError(f"{tok} requires an integer")
            limit = int(tokens[i + 1])
            i += 2
            continue
        if tok in ("-o", "--output"):
            if i + 1 >= len(tokens):
                raise ValueError(f"{tok} requires a path")
            output = tokens[i + 1]
            i += 2
            continue
        if tok in ("-x", "--xml"):
            want_xml = True
            i += 1
            continue
        if tok in ("-p", "--pdf"):
            want_pdf = True
            i += 1
            continue
        if tok in ("-n", "--noexecute"):
            noexecute = True
            i += 1
            continue
        if tok in ("-h", "--help"):
            raise SystemExit(_help_text())

        if tok in _IGNORED_FLAGS:
            warnings.append(f"Ignoring unsupported pygetpapers flag: {tok}")
            i += 1
            continue
        if tok in _IGNORED_WITH_VALUE or (
            tok.startswith("-") and tok not in _SUPPORTED
        ):
            # Skip flag and optional following value if it does not look like a flag
            warnings.append(f"Ignoring unsupported pygetpapers option: {tok}")
            i += 1
            if i < len(tokens) and not tokens[i].startswith("-"):
                warnings.append(f"  (skipped value: {tokens[i]})")
                i += 1
            continue

        # Bare query string without -q (rare); take as query if none yet
        if not tok.startswith("-") and query is None:
            query = tok
            i += 1
            continue

        raise ValueError(f"Unrecognized pygetpapers argument: {tok}")

    if not query or not str(query).strip():
        raise ValueError(
            "pygetpapers translation requires -q/--query. "
            "Example: semantic_corpus --pygetpapers -q 'AMOC AND India' -k 50 -o out -x"
        )

    formats: List[str] = []
    if want_xml:
        formats.append("xml")
    if want_pdf:
        formats.append("pdf")

    command = "search" if (noexecute or not formats) else "download"
    if not formats and not noexecute:
        warnings.append(
            "No -x/--xml or -p/--pdf given; running search only "
            "(metadata → search_results.json). Add -x and/or -p to download."
        )

    return TranslatedPygetpapers(
        query=str(query).strip(),
        limit=limit,
        output=output,
        formats=formats,
        noexecute=noexecute or not formats,
        warnings=warnings,
        command=command,
    )


def _help_text() -> str:
    return """\
Translate a pygetpapers-style invocation into semantic_corpus search/download.

  semantic_corpus --pygetpapers -q 'AMOC AND India' -k 50 -o temp/queries/amoc_india_2026 -x

Supported pygetpapers flags:
  -q/--query   query string (Europe PMC syntax; keep quotes in the shell)
  -k/--limit   max hits (default 100)
  -o/--output  output directory
  -x/--xml     download XML
  -p/--pdf     download PDF
  -n/--noexecute   search only (no download)

Unsupported flags (--supp, --zip, --makecsv, --synonym, …) are ignored with a warning.

Native equivalent after translation:
  semantic_corpus download -q '…' -l 50 -o … -f xml -r europe_pmc
"""


def run_pygetpapers_translation(argv: Sequence[str]) -> int:
    """Parse pygetpapers argv, print translation, run search/download. Return exit code."""
    from semantic_corpus.cli import (
        create_parser,
        download_papers_command,
        search_papers_command,
    )

    try:
        translated = parse_pygetpapers_argv(argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        # ``--help`` raises SystemExit with the help text as the payload
        msg = exc.code
        if isinstance(msg, str):
            print(msg)
            return 0
        return int(msg) if msg is not None else 0

    for warning in translated.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    sc_argv = translated.to_semantic_corpus_argv()
    print("Translated to: semantic_corpus " + " ".join(shlex.quote(a) for a in sc_argv))

    parser = create_parser()
    args = parser.parse_args(sc_argv)
    try:
        if args.command == "search":
            search_papers_command(args)
        elif args.command == "download":
            download_papers_command(args)
        else:
            print(f"Internal error: unexpected command {args.command}", file=sys.stderr)
            return 1
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1
    return 0
