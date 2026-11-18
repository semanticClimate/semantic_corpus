#!/usr/bin/env python3
"""Rebuild phrases → encyclopedia (CLI wrapper).

Preferred::

  ./venv/bin/pipeline encyclopedia --workdir corpora/amoc_insolation_20 \\
      --min-paper-count 2 --max-entries 50 --force

  ./venv/bin/pipeline encyclopedia --workdir corpora/amoc_insolation_20 \\
      --rebuild-phrases --force
"""

from __future__ import annotations

import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    from semantic_corpus.pipeline.cli import main as pipeline_main

    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] != "encyclopedia":
        raw = ["encyclopedia", *raw]
    return pipeline_main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
