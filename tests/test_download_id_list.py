"""Tests for download progress id list formatting."""

from __future__ import annotations

from semantic_corpus.repositories._ids import short_display_id
from semantic_corpus.utils import print_id_list, wrap_space_separated


def test_short_display_id_pmcid() -> None:
    assert short_display_id("europe_pmc_PMC12787522") == "PMC12787522"
    assert short_display_id({"pmcid": "PMC13148317"}) == "PMC13148317"
    assert short_display_id("PMC13440228") == "PMC13440228"


def test_wrap_space_separated() -> None:
    names = [f"PMC{i:08d}" for i in range(12)]
    text = wrap_space_separated(names, width=40)
    assert "\n" in text
    assert "PMC00000000" in text
    assert "INFO" not in text


def test_print_id_list(capsys) -> None:
    print_id_list(["PMC1", "PMC2", "PMC3"], width=20, file=None)
    # print_id_list defaults to stderr
    err = capsys.readouterr().err
    assert "PMC1 PMC2 PMC3" in err.replace("\n", " ")
