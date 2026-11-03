"""Tests for the encyclopedia step.

Selection tests use on-disk fixtures (no network).
Resolve / build / CLI tests hit the **live** MediaWiki API (no mocks).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.cluster_review.encyclopedia import (
    build_encyclopedia,
    encyclopedia_is_current,
    load_entries,
    resolve_phrase_wikipedia,
    select_phrases,
)


def _write_mini_corpus(root: Path) -> Path:
    """Clusters JSON for selection / live resolve tests."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "clusters").mkdir(exist_ok=True)
    (root / "phrases").mkdir(exist_ok=True)
    clusters = {
        "step": 3,
        "clusters": [
            {
                "cluster_id": 1,
                "paper_ids": ["p1", "p2"],
                "terms": [
                    {
                        "phrase": "atlantic meridional overturning circulation",
                        "display": "Atlantic Meridional Overturning Circulation",
                        "weight": 5.0,
                    },
                    {"phrase": "amoc", "display": "AMOC", "weight": 4.0},
                    {
                        "phrase": "north atlantic",
                        "display": "North Atlantic",
                        "weight": 2.0,
                    },
                    {"phrase": "noise term", "display": "Noise Term", "weight": 0.1},
                ],
            }
        ],
    }
    (root / "clusters" / "clusters.json").write_text(
        json.dumps(clusters), encoding="utf-8"
    )
    (root / "phrases" / "index.json").write_text(
        json.dumps({"paper_count": 2, "unique_phrases": 4}), encoding="utf-8"
    )
    return root


def test_select_phrases_ranks_and_truncates(tmp_path: Path):
    workdir = _write_mini_corpus(tmp_path / "corp")
    selected, source = select_phrases(workdir, max_entries=2)
    assert source == "clusters"
    assert [c["phrase"] for c in selected] == [
        "atlantic meridional overturning circulation",
        "amoc",
    ]
    assert selected[0]["display"].startswith("Atlantic")


def test_select_phrases_respects_demoted_terms(tmp_path: Path):
    workdir = _write_mini_corpus(tmp_path / "corp")
    (workdir / "clusters" / "demoted_terms.json").write_text(
        json.dumps({"terms": ["amoc"]}), encoding="utf-8"
    )
    selected, source = select_phrases(workdir, max_entries=10)
    assert source == "clean"
    phrases = [c["phrase"] for c in selected]
    assert "amoc" not in phrases
    assert "atlantic meridional overturning circulation" in phrases


def test_select_phrases_min_score_and_phrases_source(tmp_path: Path):
    workdir = _write_mini_corpus(tmp_path / "corp")
    # Phrase caches with TF-IDF-like scores (no phrases_terms.csv → caches)
    (workdir / "phrases" / "p1.json").write_text(
        json.dumps(
            {
                "paper_id": "p1",
                "phrases": [
                    {
                        "phrase": "atlantic meridional overturning circulation",
                        "display": "AMOC full",
                        "score": 0.9,
                    },
                    {"phrase": "weak phrase", "display": "Weak", "score": 0.05},
                ],
            }
        ),
        encoding="utf-8",
    )
    selected, source = select_phrases(
        workdir, max_entries=10, min_score=0.2, source="phrases"
    )
    assert source == "phrases"
    phrases = [c["phrase"] for c in selected]
    assert "atlantic meridional overturning circulation" in phrases
    assert "weak phrase" not in phrases

    selected2, _ = select_phrases(workdir, max_entries=10, min_score=3.0)
    # cluster weights: amoc=4, atlantic…=5 — noise 0.1 dropped
    assert all(c["score"] >= 3.0 for c in selected2)


def test_apply_disambiguation_acronym_offline():
    """encyclopedia resolve_disambiguation picks SST from paper acronym context."""
    from semantic_corpus.cluster_review.encyclopedia_disambiguation import (
        apply_encyclopedia_disambiguation,
        needs_disambiguation,
    )

    try:
        from encyclopedia.pipeline.wikipedia_disambiguation import (  # noqa: F401
            resolve_disambiguation,
        )
    except ImportError as exc:
        pytest.skip(f"encyclopedia package unavailable: {exc}")

    entry = {
        "phrase": "sst",
        "display": "SST",
        "status": "ambiguous",
        "wiki_lang": "en",
        "wiki_title": "SST",
        "wiki_url": "https://en.wikipedia.org/wiki/SST",
        "candidates": [
            {
                "title": "Sea surface temperature",
                "snippet": "ocean temperature",
            },
            {
                "title": "Supersonic transport",
                "snippet": "aircraft",
            },
            {"title": "SST (disambiguation)", "snippet": "dab"},
        ],
    }
    assert needs_disambiguation(entry)
    leads = {
        "sea surface temperature": (
            "Sea surface temperature is the water temperature close to the ocean surface."
        ),
        "supersonic transport": (
            "A supersonic transport is a civilian aircraft designed to transport passengers at speeds greater than the speed of sound."
        ),
    }
    # Avoid live title fill when chosen — pass empty session path by using leads only;
    # _fill_from_title still hits network. Stub by checking decision fields via direct resolve.
    from encyclopedia.pipeline.wikipedia_disambiguation import (
        disambiguation_page_html,
        resolve_disambiguation,
    )

    html = disambiguation_page_html(
        "sst may refer to:",
        [
            ("Sea surface temperature", "ocean temperature"),
            ("Supersonic transport", "aircraft"),
        ],
    )
    sentences = [
        "The sea surface temperature (SST) anomaly was positive across the North Atlantic."
    ]
    decision = resolve_disambiguation("sst", html, sentences, leads=leads)
    assert decision.status == "resolved"
    assert decision.chosen_title == "Sea surface temperature"

    result = apply_encyclopedia_disambiguation(
        entry, sentences=sentences, leads=leads, fill_title=False
    )
    assert result.get("disambiguation_status") == "resolved"
    assert result.get("status") == "resolved"
    assert result.get("wiki_title") == "Sea surface temperature"
    assert result.get("pointer_kind") == "disambiguation"


def test_entries_to_ami_dicts_maps_pipeline_fields():
    from semantic_corpus.cluster_review.encyclopedia_html import entries_to_ami_dicts

    rows = entries_to_ami_dicts(
        [
            {
                "phrase": "amoc",
                "display": "AMOC",
                "status": "resolved",
                "wiki_url": "https://en.wikipedia.org/wiki/Atlantic_meridional_overturning_circulation",
                "wikidata_id": "Q625632",
            },
            {"phrase": "bad", "status": "error"},
            {
                "phrase": "missing term",
                "display": "Missing Term",
                "status": "missing",
                "wiki_url": "https://en.wikipedia.org/wiki/X",
                "wikidata_id": "Q1",
            },
        ]
    )
    assert [r["search_term"] for r in rows] == ["amoc", "missing term"]
    assert rows[0]["wikipedia_url"].endswith("circulation")
    assert rows[0]["wikidata_id"] == "Q625632"
    assert rows[1]["wikipedia_url"] == ""
    assert rows[1]["wikidata_id"] == ""


def test_write_encyclopedia_html_offline(tmp_path: Path):
    """AmiEncyclopedia HTML without re-fetching Wikipedia descriptions."""
    from semantic_corpus.cluster_review.encyclopedia_html import (
        ensure_encyclopedia_on_path,
        write_encyclopedia_html,
    )

    try:
        ensure_encyclopedia_on_path()
    except Exception as exc:
        pytest.skip(f"encyclopedia package unavailable: {exc}")

    workdir = tmp_path / "corp"
    (workdir / "encyclopedia").mkdir(parents=True)
    doc = {
        "step": "encyclopedia",
        "entries": [
            {
                "phrase": "amoc",
                "display": "AMOC",
                "status": "resolved",
                "wiki_url": "https://en.wikipedia.org/wiki/Atlantic_meridional_overturning_circulation",
                "wikidata_id": "Q625632",
                "description_html": "<p>The AMOC is a system of ocean currents.</p>",
            },
            {
                "phrase": "northern hemisphere",
                "display": "Northern Hemisphere",
                "status": "resolved",
                "wiki_url": "https://en.wikipedia.org/wiki/Northern_Hemisphere",
                "wikidata_id": "Q39061",
                "description_html": "<p>The Northern Hemisphere is north of the equator.</p>",
            },
        ],
    }
    (workdir / "encyclopedia" / "entries.json").write_text(
        __import__("json").dumps(doc), encoding="utf-8"
    )
    out = write_encyclopedia_html(
        workdir,
        entries_doc=doc,
        title="Test Encyclopedia",
        fetch_descriptions=False,
    )
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert 'role="ami_entry"' in html or "ami_entry" in html
    assert "AMOC" in html or "Northern Hemisphere" in html


def test_select_phrases_from_phrases_terms_min_paper_count(tmp_path: Path):
    workdir = tmp_path / "corp"
    (workdir / "phrases").mkdir(parents=True)
    (workdir / "phrases" / "phrases_terms.csv").write_text(
        "phrase,display,n_papers,best_score,score_channel\n"
        "north atlantic,North Atlantic,13,6.9,uppercase\n"
        "amoc,AMOC,2,2.64,uppercase\n"
        "singleton,Singleton,1,4.0,uppercase\n",
        encoding="utf-8",
    )
    selected, source = select_phrases(
        workdir, max_entries=50, min_paper_count=2, source="phrases"
    )
    assert source == "phrases_terms"
    phrases = [c["phrase"] for c in selected]
    assert phrases == ["north atlantic", "amoc"]
    assert selected[0]["n_papers"] == 13
    assert "singleton" not in phrases


def test_kg_plan_depends_on_clusters_not_encyclopedia():
    from semantic_corpus.pipeline.steps import required_steps

    plan = required_steps(["encyclopedia"], from_mode="existing")
    assert plan == ["corpus", "phrases", "clusters", "encyclopedia"]
    assert "clean" not in plan

    kg_plan = required_steps(["kg"], from_mode="existing")
    assert kg_plan == ["corpus", "phrases", "clusters", "kg"]
    assert "encyclopedia" not in kg_plan


@pytest.mark.live_api
@pytest.mark.network
def test_resolve_phrase_wikipedia_live_amoc():
    result = resolve_phrase_wikipedia("amoc", lang="en")
    assert result["status"] in {"resolved", "ambiguous"}
    assert result.get("wiki_title")
    assert result.get("wiki_url", "").startswith("https://en.wikipedia.org/")
    # Wikidata id is usual but not mandatory if pageprops missing
    if result.get("wikidata_id"):
        assert result["wikidata_id"].startswith("Q")


@pytest.mark.live_api
@pytest.mark.network
def test_build_encyclopedia_live(tmp_path: Path):
    workdir = _write_mini_corpus(tmp_path / "corp")
    doc = build_encyclopedia(
        workdir,
        lang="en",
        max_entries=2,
        force=True,
        sleep_s=0.15,
        write_html=False,
    )
    assert doc["params"]["max_entries"] == 2
    assert doc["params"]["phrase_source"] == "clusters"
    assert doc["counts"]["selected"] == 2
    assert doc["counts"]["error"] == 0
    assert (workdir / "encyclopedia" / "entries.json").is_file()
    assert (workdir / "encyclopedia" / "fetch_log.jsonl").is_file()

    loaded = load_entries(workdir)
    assert loaded is not None
    assert len(loaded["entries"]) == 2
    for entry in loaded["entries"]:
        assert entry["status"] in {"resolved", "ambiguous", "missing"}
        if entry["status"] in {"resolved", "ambiguous"}:
            assert entry.get("wiki_title")

    assert encyclopedia_is_current(
        workdir, lang="en", max_entries=2, require_html=False
    )
    assert not encyclopedia_is_current(
        workdir, lang="en", max_entries=1, require_html=False
    )

    # Second run uses disk cache (still no fakes)
    doc2 = build_encyclopedia(
        workdir,
        lang="en",
        max_entries=2,
        force=False,
        sleep_s=0,
        write_html=False,
    )
    assert doc2["counts"]["cached"] == 2
    assert doc2["counts"]["fetched"] == 0


@pytest.mark.live_api
@pytest.mark.network
@pytest.mark.slow
def test_pipeline_cli_encyclopedia_live():
    """Real pipeline CLI against corpora/amoc_insolation_20 (needs clusters)."""
    import shutil

    pytest.importorskip("doit")

    from semantic_corpus.pipeline.cli import main
    from semantic_corpus.pipeline.placeholders import stamp_path

    workdir = Path("corpora/amoc_insolation_20").resolve()
    if not (workdir / "clusters" / "clusters.json").is_file():
        pytest.skip("corpora/amoc_insolation_20 clusters missing; run clusters first")

    # Invalidate encyclopedia only (do not --always remake corpus/phrases/clusters).
    enc_dir = workdir / "encyclopedia"
    if enc_dir.is_dir():
        shutil.rmtree(enc_dir)
    stamp = stamp_path("encyclopedia", workdir)
    if stamp.is_file():
        stamp.unlink()

    assert (
        main(
            [
                "--workdir",
                str(workdir),
                "--encyclopedia-lang",
                "en",
                "--max-entries",
                "3",
                "--target",
                "encyclopedia",
            ]
        )
        == 0
    )
    doc = load_entries(workdir)
    assert doc is not None
    assert doc["counts"]["selected"] == 3
    assert doc["counts"]["error"] == 0
    assert stamp.is_file()
    assert (workdir / "encyclopedia" / "entries.json").is_file()
