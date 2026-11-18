"""Tests for pygetpapers → semantic_corpus CLI translator."""

from __future__ import annotations

import pytest

from semantic_corpus.cli_pygetpapers import (
    parse_pygetpapers_argv,
    run_pygetpapers_translation,
)


class TestParsePygetpapers:
    def test_xml_download(self) -> None:
        t = parse_pygetpapers_argv(
            ["-q", "AMOC AND India", "-k", "50", "-o", "temp/queries/amoc", "-x"]
        )
        assert t.query == "AMOC AND India"
        assert t.limit == 50
        assert t.output == "temp/queries/amoc"
        assert t.formats == ["xml"]
        assert t.command == "download"
        assert t.to_semantic_corpus_argv() == [
            "download",
            "--query",
            "AMOC AND India",
            "--limit",
            "50",
            "--output",
            "temp/queries/amoc",
            "--formats",
            "xml",
            "--repository",
            "europe_pmc",
        ]

    def test_xml_and_pdf(self) -> None:
        t = parse_pygetpapers_argv(["-q", "heatwave", "-k", "10", "-x", "-p"])
        assert t.formats == ["xml", "pdf"]
        assert t.command == "download"

    def test_noexecute_is_search(self) -> None:
        t = parse_pygetpapers_argv(["-q", "AMOC", "-n"])
        assert t.command == "search"
        assert t.noexecute is True

    def test_no_format_defaults_to_search_with_warning(self) -> None:
        t = parse_pygetpapers_argv(["-q", "AMOC", "-k", "5"])
        assert t.command == "search"
        assert any("search only" in w for w in t.warnings)

    def test_pasted_command_string(self) -> None:
        t = parse_pygetpapers_argv(
            ['pygetpapers -q "AMOC AND India" -k 50 -o out -x']
        )
        assert t.query == "AMOC AND India"
        assert t.limit == 50
        assert t.formats == ["xml"]

    def test_strips_leading_double_dash(self) -> None:
        t = parse_pygetpapers_argv(["--", "-q", "x", "-k", "1", "-x"])
        assert t.query == "x"

    def test_ignores_unsupported_with_warning(self) -> None:
        t = parse_pygetpapers_argv(["-q", "x", "-x", "--makecsv", "--synonym"])
        assert t.formats == ["xml"]
        assert any("makecsv" in w for w in t.warnings)
        assert any("synonym" in w for w in t.warnings)

    def test_missing_query_raises(self) -> None:
        with pytest.raises(ValueError, match="requires -q"):
            parse_pygetpapers_argv(["-k", "10", "-x"])

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit):
            parse_pygetpapers_argv(["--help"])


class TestRunTranslation:
    def test_run_search_mocked(self, temp_dir, monkeypatch, capsys) -> None:
        calls = {}

        def fake_search(args):
            calls["query"] = args.query
            calls["limit"] = args.limit
            calls["output"] = args.output

        monkeypatch.setattr(
            "semantic_corpus.cli.search_papers_command", fake_search
        )
        code = run_pygetpapers_translation(
            ["-q", "AMOC AND India", "-k", "3", "-o", str(temp_dir), "-n"]
        )
        assert code == 0
        assert calls["query"] == "AMOC AND India"
        assert calls["limit"] == 3
        out = capsys.readouterr().out
        assert "Translated to: semantic_corpus search" in out
