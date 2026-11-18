"""Editable Step 2 stop lists live under cluster_review/lists/."""

from __future__ import annotations

from pathlib import Path

from semantic_corpus.cluster_review import lists_loader as lists


def test_lists_dir_has_expected_files() -> None:
    d = lists.lists_dir()
    assert d.is_dir()
    for name in (
        "phrase_boilerplate.txt",
        "latex_noise.txt",
        "proper_boilerplate.txt",
        "common_titlecase.txt",
        "acronym_skip.txt",
        "figure_table_noise.txt",
        "README.md",
    ):
        assert Path(d, name).is_file(), name


def test_phrase_boilerplate_loads_entries() -> None:
    lists.clear_list_cache()
    words = lists.phrase_boilerplate()
    assert "et al" in words
    assert "open access" in words


def test_common_titlecase_file_exists_and_is_non_domain() -> None:
    """File is present for editing; default has no active domain gazetteer lines."""
    lists.clear_list_cache()
    active = lists.common_titlecase()
    # No uncommented domain terms by default
    assert "india" not in active
    assert "amoc" not in active
    assert "monsoon" not in active


def test_acronym_skip_preserves_case() -> None:
    lists.clear_list_cache()
    skip = lists.acronym_skip()
    assert "FIG" in skip
    assert "PDF" in skip
