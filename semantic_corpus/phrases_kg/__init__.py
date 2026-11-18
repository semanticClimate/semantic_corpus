"""Extension module: phrase extraction and bipartite knowledge graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

MODULE_NAME = "phrases_kg"


def load_meta() -> Dict[str, Any]:
    """Load ``module.yaml`` for the phrases_kg module."""
    from semantic_corpus.module_meta import load_module

    return load_module(MODULE_NAME)


def module_root() -> Path:
    """Filesystem root of this module package."""
    return Path(__file__).resolve().parent


__all__ = ["MODULE_NAME", "load_meta", "module_root"]
