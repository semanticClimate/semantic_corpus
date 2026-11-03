"""Tests for symbolic pipeline graph + runner.

Unit tests use ``PIPELINE_PLACEHOLDER=1`` (stamps only).
The AMOC×insolation example is a live Europe PMC run (limit 20).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.pipeline.config import ENV_PLACEHOLDER, infer_from_mode
from semantic_corpus.pipeline.placeholders import stamp_path
from semantic_corpus.pipeline.steps import (
    deps_for,
    required_steps,
)


doit = pytest.importorskip(
    "doit",
    reason="pipeline tests need doit — pip install 'semantic_corpus[test]' or pip install doit",
)


@pytest.fixture(autouse=True)
def _pipeline_placeholder_mode(monkeypatch, request):
    """Stamp-only unless the test is marked live_api / network."""
    markers = {m.name for m in request.node.iter_markers()}
    if markers & {"live_api", "network"}:
        monkeypatch.delenv(ENV_PLACEHOLDER, raising=False)
    else:
        monkeypatch.setenv(ENV_PLACEHOLDER, "1")


def test_infer_from_mode():
    assert infer_from_mode("amoc AND India", None) == "query"
    assert infer_from_mode(None, "wg2/ch2") == "documents"
    assert infer_from_mode(None, None) == "existing"
    with pytest.raises(ValueError):
        infer_from_mode("q", "s")


def test_deps_corpus_modes():
    assert deps_for("corpus", "query") == ["query"]
    assert deps_for("corpus", "documents") == ["documents"]
    assert deps_for("corpus", "existing") == []
    assert deps_for("phrases", "query") == ["corpus"]
    assert deps_for("pdfs", "query") == ["corpus"]
    assert deps_for("clusters", "query") == ["phrases"]


def test_required_steps_clusters_via_query():
    plan = required_steps(["clusters"], from_mode="query")
    assert plan == ["query", "corpus", "phrases", "clusters"]
    assert "pdfs" not in plan
    assert "bagit" not in plan


def test_required_steps_existing():
    plan = required_steps(["clusters"], from_mode="existing")
    assert plan == ["corpus", "phrases", "clusters"]


def test_cli_placeholder_query_to_clusters(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    workdir = tmp_path / "corpora" / "amoc"
    assert (
        main(
            [
                "--workdir",
                str(workdir),
                "--query",
                "amoc AND insolation",
                "--limit",
                "20",
                "--phrase-method",
                "tfidf",
                "--cluster-resolution",
                "0.8",
                "--target",
                "clusters",
            ]
        )
        == 0
    )
    for step in ("query", "corpus", "phrases", "clusters"):
        assert stamp_path(step, workdir).is_file(), step
    data = json.loads(stamp_path("query", workdir).read_text(encoding="utf-8"))
    assert data["options"]["limit"] == 20
    assert data["status"] == "placeholder"


@pytest.mark.live_api
@pytest.mark.network
@pytest.mark.slow
def test_example_amoc_insolation_limit_20_to_clusters():
    """Live tutorial example — writes under project ``--workdir``::

        pipeline --workdir corpora/amoc_insolation_20 \\
          --query "amoc AND insolation" --limit 20 \\
          --phrase-method tfidf --phrase-n 3 --phrase-top 15 \\
          --cluster-resolution 0.8 \\
          --target clusters

    Results stay in that corpus (not pytest tmp). Harvest XMLs also land in
    ``temp/queries/amoc_insolation_20/``.
    """
    pytest.importorskip("sklearn")
    pytest.importorskip("networkx")

    from semantic_corpus.pipeline.cli import main

    # Same contract as the CLI: corpus root is --workdir.
    # Use ``run --always`` so a prior successful corpus is remade (otherwise
    # skip-if-done finishes in seconds and never hits Europe PMC again).
    workdir = Path("corpora/amoc_insolation_20").resolve()
    argv = [
        "run",
        "--always",
        "--workdir",
        str(workdir),
        "--query",
        "amoc AND insolation",
        "--limit",
        "20",
        "--phrase-method",
        "tfidf",
        "--phrase-n",
        "3",
        "--phrase-top",
        "15",
        "--cluster-resolution",
        "0.8",
        "--target",
        "clusters",
    ]

    assert required_steps(["clusters"], from_mode="query") == [
        "query",
        "corpus",
        "phrases",
        "clusters",
    ]
    assert main(argv) == 0

    assert (workdir / "bagit.txt").is_file()
    assert (workdir / "phrases" / "index.json").is_file()
    assert (workdir / "clusters" / "graph_summary.json").is_file()
    assert (workdir / "clusters" / "clusters.json").is_file()

    index = json.loads((workdir / "phrases" / "index.json").read_text(encoding="utf-8"))
    paper_count = int(index.get("paper_count") or 0)
    assert 1 <= paper_count <= 20

    summary = json.loads(
        (workdir / "clusters" / "graph_summary.json").read_text(encoding="utf-8")
    )
    assert summary.get("paper_count") == paper_count
    assert int(summary.get("cluster_count") or 0) >= 0
    assert summary.get("params", {}).get("resolution") == 0.8

    query_stamp = json.loads(stamp_path("query", workdir).read_text(encoding="utf-8"))
    assert query_stamp["status"] == "ok"
    assert query_stamp["options"]["query"] == "amoc AND insolation"
    assert query_stamp["options"]["limit"] == 20
    assert int(query_stamp.get("paper_count") or paper_count) <= 20


def test_cli_query_also_stamps_corpus(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main
    from semantic_corpus.pipeline.placeholders import read_stamp

    assert (
        main(
            [
                "--workdir",
                str(tmp_path),
                "--query",
                "AMOC AND India",
                "--target",
                "corpus",
            ]
        )
        == 0
    )
    assert stamp_path("query", tmp_path).is_file()
    assert stamp_path("corpus", tmp_path).is_file()
    corpus = read_stamp("corpus", tmp_path)
    assert corpus is not None
    assert corpus.get("produced_by") == "query"


def test_cli_source_to_clusters(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    assert (
        main(
            [
                "--workdir",
                str(tmp_path),
                "--source",
                "wg2/chapter[2-6]",
                "--target",
                "clusters",
            ]
        )
        == 0
    )
    assert stamp_path("documents", tmp_path).is_file()
    assert stamp_path("corpus", tmp_path).is_file()
    assert not stamp_path("query", tmp_path).is_file()


def test_cli_existing_target_clusters(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    assert main(["--workdir", str(tmp_path), "--target", "clusters"]) == 0
    assert stamp_path("corpus", tmp_path).is_file()
    assert stamp_path("phrases", tmp_path).is_file()
    assert stamp_path("clusters", tmp_path).is_file()
    assert not stamp_path("query", tmp_path).is_file()


def test_cli_query_and_source_rejected(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    rc = main(
        [
            "--workdir",
            str(tmp_path),
            "--query",
            "x",
            "--source",
            "y",
            "--target",
            "clusters",
        ]
    )
    assert rc == 2


def test_kg_plan_after_clusters():
    plan = required_steps(["kg"], from_mode="existing")
    assert plan == [
        "corpus",
        "phrases",
        "clusters",
        "kg",
    ]
    assert "encyclopedia" not in plan
    assert "clean" not in plan


def test_options_max_entries_and_kg_links():
    from pathlib import Path as P

    from semantic_corpus.pipeline.config import PipelineOptions

    opts = PipelineOptions(
        workdir=P("."),
        from_mode="existing",
        max_entries=50,
        kg_links="clusters,wikipedia",
    )
    assert opts.max_entries == 50
    assert opts.kg_link_list() == ("clusters", "wikipedia")

    with pytest.raises(ValueError, match="max-entries"):
        PipelineOptions(workdir=P("."), from_mode="existing", max_entries=0)
    with pytest.raises(ValueError, match="kg-links"):
        PipelineOptions(
            workdir=P("."), from_mode="existing", kg_links="clusters,nope"
        )


def test_cli_encyclopedia_max_entries_and_kg_links(tmp_path: Path):
    """Stub encyclopedia/kg accept --max-entries and --kg-links (placeholder)."""
    from semantic_corpus.pipeline.cli import main

    assert (
        main(
            [
                "--workdir",
                str(tmp_path),
                "--max-entries",
                "50",
                "--encyclopedia-lang",
                "en",
                "--kg-links",
                "clusters,wikipedia,wikidata",
                "--kg-max-island",
                "15",
                "--target",
                "kg",
            ]
        )
        == 0
    )
    for step in (
        "corpus",
        "phrases",
        "clusters",
        "kg",
    ):
        assert stamp_path(step, tmp_path).is_file(), step
    assert not stamp_path("clean", tmp_path).is_file()
    # encyclopedia is optional for kg (soft-attach when entries exist)
    assert not stamp_path("encyclopedia", tmp_path).is_file()

    kg = json.loads(stamp_path("kg", tmp_path).read_text(encoding="utf-8"))
    assert kg["options"]["max_entries"] == 50
    assert kg["options"]["encyclopedia_lang"] == "en"
    assert kg["options"]["kg_links"] == "clusters,wikipedia,wikidata"
    assert kg["options"]["kg_max_island"] == 15
    assert kg["status"] == "placeholder"


def test_cli_invalid_kg_links_rejected(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    rc = main(
        [
            "--workdir",
            str(tmp_path),
            "--kg-links",
            "clusters,bogus",
            "--target",
            "kg",
        ]
    )
    assert rc == 2


def test_cli_second_run_skips(tmp_path: Path, capsys):
    from semantic_corpus.pipeline.cli import main

    args = [
        "--workdir",
        str(tmp_path),
        "--query",
        "AMOC AND India",
        "--target",
        "clusters",
    ]
    assert main(args) == 0
    mtimes = {
        s: stamp_path(s, tmp_path).stat().st_mtime_ns
        for s in ("query", "corpus", "phrases", "clusters")
    }
    capsys.readouterr()
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "[pipeline] query: placeholder" not in out
    for step, prev in mtimes.items():
        assert stamp_path(step, tmp_path).stat().st_mtime_ns == prev
