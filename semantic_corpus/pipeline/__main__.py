"""``python -m semantic_corpus.pipeline`` → same as the ``pipeline`` console script."""

from __future__ import annotations

import sys

from semantic_corpus.pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
