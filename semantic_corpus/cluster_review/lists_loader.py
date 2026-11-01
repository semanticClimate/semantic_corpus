"""Load editable stop / noise lists for cluster-review Step 2.

Lists live in ``semantic_corpus/cluster_review/lists/*.txt`` (one entry per line;
``#`` comments and blank lines ignored). Edit those files to change behaviour.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import FrozenSet

LISTS_DIR = Path(__file__).resolve().parent / "lists"


def load_word_list(filename: str, *, lowercase: bool = True) -> FrozenSet[str]:
    """Load a stop/noise list from ``lists/<filename>``."""
    path = Path(LISTS_DIR, filename)
    if not path.is_file():
        return frozenset()
    entries: set[str] = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries.add(line.lower() if lowercase else line)
    return frozenset(entries)


@lru_cache(maxsize=None)
def phrase_boilerplate() -> FrozenSet[str]:
    return load_word_list("phrase_boilerplate.txt", lowercase=True)


@lru_cache(maxsize=None)
def latex_noise() -> FrozenSet[str]:
    return load_word_list("latex_noise.txt", lowercase=True)


@lru_cache(maxsize=None)
def proper_boilerplate() -> FrozenSet[str]:
    return load_word_list("proper_boilerplate.txt", lowercase=True)


@lru_cache(maxsize=None)
def common_titlecase() -> FrozenSet[str]:
    return load_word_list("common_titlecase.txt", lowercase=True)


@lru_cache(maxsize=None)
def acronym_skip() -> FrozenSet[str]:
    # Keep uppercase form as in file for matching raw ALLCAPS tokens
    return load_word_list("acronym_skip.txt", lowercase=False)


@lru_cache(maxsize=None)
def figure_table_noise() -> FrozenSet[str]:
    return load_word_list("figure_table_noise.txt", lowercase=True)


@lru_cache(maxsize=None)
def scientific_discourse() -> FrozenSet[str]:
    """Manuscript / discourse furniture (figures, supplementary data, …)."""
    return load_word_list("scientific_discourse.txt", lowercase=True)


def clear_list_cache() -> None:
    """Clear cached lists (e.g. after editing files in the same process)."""
    phrase_boilerplate.cache_clear()
    latex_noise.cache_clear()
    proper_boilerplate.cache_clear()
    common_titlecase.cache_clear()
    acronym_skip.cache_clear()
    figure_table_noise.cache_clear()
    scientific_discourse.cache_clear()


def lists_dir() -> Path:
    return LISTS_DIR
