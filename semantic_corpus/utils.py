"""Utility functions for semantic_corpus."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, TextIO


def wrap_space_separated(
    names: Sequence[str],
    *,
    width: int = 78,
) -> str:
    """Join names with spaces and wrap to ``width`` (no INFO prefixes)."""
    body = " ".join(str(n) for n in names if n)
    if not body:
        return ""
    return textwrap.fill(body, width=width)


def print_id_list(
    names: Iterable[str],
    *,
    width: int = 78,
    file: Optional[TextIO] = None,
) -> List[str]:
    """Print a line-wrapped, space-separated id list; return the cleaned names."""
    cleaned = [str(n).strip() for n in names if n and str(n).strip()]
    if not cleaned:
        return []
    out = file if file is not None else sys.stderr
    print(wrap_space_separated(cleaned, width=width), file=out, flush=True)
    return cleaned


def get_project_temp_dir() -> Path:
    """Get the project temp directory."""
    return Path(Path(__file__).parent.parent, "temp")


def get_downloads_dir() -> Path:
    """Get the downloads directory within project temp."""
    downloads_dir = Path(get_project_temp_dir(), "downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    return downloads_dir


def get_corpus_dir() -> Path:
    """Get the corpus directory within project temp."""
    corpus_dir = Path(get_project_temp_dir(), "corpus")
    corpus_dir.mkdir(parents=True, exist_ok=True)
    return corpus_dir


def get_logs_dir() -> Path:
    """Get the logs directory within project temp."""
    logs_dir = Path(get_project_temp_dir(), "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_test_results_dir() -> Path:
    """Get the test results directory within project temp."""
    test_dir = Path(get_project_temp_dir(), "test_results")
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir
