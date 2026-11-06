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
    assert infer_from_mode("amoc AND India", None) == "collect"
    assert infer_from_mode(None, "wg2/ch2") == "collect"
    assert infer_from_mode(None, None) == "existing"
    with pytest.raises(ValueError):
        infer_from_mode("q", "s")


def test_deps_corpus_modes():
    assert deps_for("corpus", "collect") == ["collect"]
    assert deps_for("corpus", "existing") == []
    assert deps_for("phrases", "collect") == ["corpus"]
    assert deps_for("pdfs", "collect") == ["corpus"]
    assert deps_for("clusters", "collect") == ["phrases"]
    assert deps_for("clean", "collect") == ["clusters"]
    assert deps_for("encyclopedia", "collect") == ["clean"]


def test_required_steps_clusters_via_query():
    plan = required_steps(["clusters"], from_mode="collect")
    assert plan == ["collect", "corpus", "phrases", "clusters"]
    assert "pdfs" not in plan
    assert "encyclopedia" not in plan
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
    for step in ("collect", "corpus", "phrases", "clusters"):
        assert stamp_path(step, workdir).is_file(), step
    data = json.loads(stamp_path("collect", workdir).read_text(encoding="utf-8"))
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

    assert required_steps(["clusters"], from_mode="collect") == [
        "collect",
        "corpus",
        "phrases",
        "clusters",
    ]
    assert main(argv) == 0

    assert (workdir / "bagit.txt").is_file()
    assert (workdir / "packets" / "manifest.json").is_file()
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

    query_stamp = json.loads(stamp_path("collect", workdir).read_text(encoding="utf-8"))
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
    assert stamp_path("collect", tmp_path).is_file()
    assert stamp_path("corpus", tmp_path).is_file()
    corpus = read_stamp("corpus", tmp_path)
    assert corpus is not None
    assert corpus.get("produced_by") == "collect"


def test_cli_source_to_clusters(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main
    from semantic_corpus.pipeline.placeholders import read_stamp

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
    assert stamp_path("collect", tmp_path).is_file()
    assert stamp_path("corpus", tmp_path).is_file()
    corpus = read_stamp("corpus", tmp_path)
    assert corpus is not None
    assert corpus.get("produced_by") == "collect"


def test_cli_existing_target_clusters(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    assert main(["--workdir", str(tmp_path), "--target", "clusters"]) == 0
    assert stamp_path("corpus", tmp_path).is_file()
    assert stamp_path("phrases", tmp_path).is_file()
    assert stamp_path("clusters", tmp_path).is_file()
    assert not stamp_path("collect", tmp_path).is_file()


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


def test_encyclopedia_plan_includes_clean():
    plan = required_steps(["encyclopedia"], from_mode="existing")
    assert plan == [
        "corpus",
        "phrases",
        "clusters",
        "clean",
        "encyclopedia",
    ]


def test_clean_plan_stops_before_encyclopedia():
    plan = required_steps(["clean"], from_mode="collect")
    assert plan == [
        "collect",
        "corpus",
        "phrases",
        "clusters",
        "clean",
    ]
    assert "encyclopedia" not in plan


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


def test_cli_encyclopedia_max_entries_and_kg_flag(tmp_path: Path):
    """Encyclopedia accepts --max-entries / --kg-links; --kg is a flag not a step."""
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
                "--kg",
                "--target",
                "encyclopedia",
            ]
        )
        == 0
    )
    for step in (
        "corpus",
        "phrases",
        "clusters",
        "clean",
        "encyclopedia",
    ):
        assert stamp_path(step, tmp_path).is_file(), step
    assert not stamp_path("kg", tmp_path).is_file()

    enc = json.loads(stamp_path("encyclopedia", tmp_path).read_text(encoding="utf-8"))
    assert enc["options"]["max_entries"] == 50
    assert enc["options"]["encyclopedia_lang"] == "en"
    assert enc["options"]["kg_links"] == "clusters,wikipedia,wikidata"
    assert enc["options"]["kg_max_island"] == 15
    assert enc["options"]["write_kg"] is True
    assert enc["options"]["kg_open"] is True
    assert enc["status"] == "placeholder"


def test_cli_invalid_kg_links_rejected(tmp_path: Path):
    from semantic_corpus.pipeline.cli import main

    rc = main(
        [
            "--workdir",
            str(tmp_path),
            "--kg-links",
            "clusters,bogus",
            "--target",
            "encyclopedia",
        ]
    )
    assert rc == 2


def test_doit_db_lives_outside_bag_root(tmp_path: Path, monkeypatch):
    """bagit.make_bag must not be able to swallow the doit dependency DB."""
    from semantic_corpus.pipeline.config import apply_env, PipelineOptions
    from semantic_corpus.pipeline.placeholders import doit_db_path

    workdir = tmp_path / "corpora" / "agri"
    workdir.mkdir(parents=True)
    apply_env(PipelineOptions(workdir=workdir, from_mode="existing"))
    db = doit_db_path(workdir)
    assert db.parent.is_dir()
    assert workdir not in db.parents and db.parent != workdir
    assert not str(db).startswith(str(workdir))


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
        for s in ("collect", "corpus", "phrases", "clusters")
    }
    capsys.readouterr()
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "[pipeline] collect: placeholder" not in out
    for step, prev in mtimes.items():
        assert stamp_path(step, tmp_path).stat().st_mtime_ns == prev
