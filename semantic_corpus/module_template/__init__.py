"""Template package for a semantic_corpus extension module.

Copy to ``semantic_corpus/<name>/`` and replace exports with the real public API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

MODULE_NAME = "example_module"


def load_meta() -> Dict[str, Any]:
    """Load this module's ``module.yaml``."""
    from semantic_corpus.module_meta import load_module

    return load_module(MODULE_NAME)


def module_root() -> Path:
    """Filesystem root of this module package."""
    return Path(__file__).resolve().parent


__all__ = ["MODULE_NAME", "load_meta", "module_root"]
