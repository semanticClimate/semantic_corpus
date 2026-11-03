"""Tests for cluster-review Step 2: phrases + cache.

Default path uses corpus TF-IDF (sklearn). YAKE tests inject a fake extractor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.cluster_review.step0 import create_corpus_from_query
from semantic_corpus.cluster_review.step2 import (
    DEFAULT_METHOD,
    DEFAULT_N,
    PHRASE_SCHEMA,
    clear_all_caches,
    extract_phrases,
    extract_phrases_from_text,
    extract_plain_text_from_xml,
    extract_tfidf_phrases,
    extract_yake_phrases,
    find_phrase_cache,
    load_cached_phrases,
    merge_tfidf_and_proper,
    normalize_phrase,
    paper_text_from_metadata,
    phrase_channel,
    phrases_dir_for_corpus,
    proper_phrases_from_text,
    tfidf_phrases_for_corpus,
    write_phrases_summary_csv,
)
from semantic_corpus.core.exceptions import CorpusError


class FakeYakeExtractor:
    """Deterministic stand-in for yake.KeywordExtractor (no yake install needed)."""

    def extract_keywords(self, text: str):
        text_l = (text or "").lower()
        candidates = []
        if "marine heatwave" in text_l or "heatwaves" in text_l:
            candidates.append(("marine heatwaves", 0.01))
        if "coral" in text_l:
            candidates.append(("coral reefs", 0.02))
        if "ocean warming" in text_l:
            candidates.append(("ocean warming events", 0.03))
        if "thermal stress" in text_l:
            candidates.append(("thermal stress", 0.04))
        if "indian ocean" in text_l:
            candidates.append(("indian ocean", 0.015))
        if "india" in text_l and "indian ocean" not in text_l:
            candidates.append(("india", 0.02))
        if not candidates:
            words = [w for w in text_l.replace("\n", " ").split() if len(w) > 3][:3]
            if words:
                candidates.append((" ".join(words), 0.1))
        candidates.append(("et al", 0.99))  # boilerplate filtered out
        return candidates


def _fake_search_download(
    *,
    query_string: str,
    repository: str,
    limit: int,
    output_dir: Path,
    formats,
    start_date: str = None,
    end_date: str = None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    abstracts = [
        (
            "Marine heatwaves drive coral bleaching across Pacific reef systems "
            "during prolonged ocean warming events."
        ),
        (
            "Ocean warming events increase thermal stress on tropical coral reefs "
            "and alter marine ecosystem dynamics."
        ),
    ]
    for i in range(limit):
        pmcid = f"PMC7{i:06d}"
        abstract = abstracts[i % len(abstracts)]
        # Body text is what Step 2 indexes by default (no front matter)
        Path(output_dir, f"{pmcid}.xml").write_text(
            f"""<?xml version="1.0"?>
            <article>
              <front><article-meta>
                <title-group><article-title>YAKE paper {i}</article-title></title-group>
                <abstract><p>{abstract}</p></abstract>
              </article-meta></front>
              <body><sec><title>Results</title><p>{abstract}</p></sec>
              <sec><title>References</title><p>Skip this citation block.</p></sec>
              </body>
            </article>
            """,
            encoding="utf-8",
        )
        results.append(
            {
                "pmcid": pmcid,
                "title": f"Marine heatwaves and coral reefs study {i}",
                "abstract": abstract,
                "authors": [{"fullName": "Tester"}],
                "publication_date": "2024-06-01",
            }
        )
    return results, len(results)


@pytest.fixture
def mini_bagit(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "semantic_corpus.cluster_review.step0.run_repository_search",
        _fake_search_download,
    )
    corpus_dir = Path(temp_dir, "corpora", "step2_mini")
    create_corpus_from_query(
        query_string="heatwave",
        query_name="step2_mini",
        query_dir=Path(temp_dir, "queries", "step2_mini"),
        limit=2,
        formats=["xml"],
        corpus_dir=corpus_dir,
        create_bagit=True,
    )
    return corpus_dir


@pytest.fixture
def fake_extractor() -> FakeYakeExtractor:
    return FakeYakeExtractor()


class TestHelpers:
    def test_normalize_phrase(self) -> None:
        assert normalize_phrase("  Marine  Heatwaves ") == "marine heatwaves"

    def test_select_phrase_display_recovers_acronyms_and_titlecase(self) -> None:
        from semantic_corpus.cluster_review.step2 import (
            attach_phrase_displays,
            select_phrase_display,
        )

        text = (
            "Indian summer monsoon (ISM) under NegE and ZeroE scenarios "
            "over the Indian Ocean basin."
        )
        assert select_phrase_display("ism", text) == "ISM"
        assert select_phrase_display("nege", text) == "NegE"
        assert select_phrase_display("indian ocean", text) == "Indian Ocean"
        rows = attach_phrase_displays(
            [{"phrase": "ism", "score": 1.0}, {"phrase": "nege", "score": 0.5}],
            text,
        )
        assert rows[0]["display"] == "ISM"
        assert rows[1]["display"] == "NegE"

    def test_paper_text_from_metadata(self) -> None:
        text = paper_text_from_metadata(
            {"title": "Title A", "abstract": "Abstract B"}
        )
        assert "Title A" in text
        assert "Abstract B" in text

    def test_default_n_is_three(self) -> None:
        assert DEFAULT_N == 3

    def test_default_method_is_tfidf(self) -> None:
        assert DEFAULT_METHOD == "tfidf"

    def test_extract_phrases_empty(self) -> None:
        assert extract_phrases_from_text("") == []

    def test_extract_phrases_mocked(self, fake_extractor: FakeYakeExtractor) -> None:
        phrases = extract_phrases_from_text(
            "Marine heatwaves affect coral reefs.",
            top=10,
            extractor=fake_extractor,
        )
        assert [p["phrase"] for p in phrases] == ["marine heatwaves", "coral reefs"]
        assert phrases[0]["score"] == 0.01
        assert all(p["channel"] == "yake" for p in phrases)

    def test_merge_tags_uppercase_and_tfidf_channels(self) -> None:
        merged = merge_tfidf_and_proper(
            [{"phrase": "particle flux", "score": 0.05}],
            [
                {
                    "phrase": "north atlantic",
                    "display": "North Atlantic",
                    "score": 20.0,
                }
            ],
            top=10,
        )
        by_phrase = {p["phrase"]: p for p in merged}
        assert by_phrase["north atlantic"]["channel"] == "uppercase"
        assert by_phrase["north atlantic"]["score"] >= 1.0
        assert by_phrase["particle flux"]["channel"] == "tfidf"
        assert by_phrase["particle flux"]["score"] < 0.1

    def test_phrase_channel_infers_legacy_tfidf_scale(self) -> None:
        assert phrase_channel({"score": 1.3}, method="tfidf") == "uppercase"
        assert phrase_channel({"score": 0.04}, method="tfidf") == "tfidf"
        assert phrase_channel({"score": 0.04}, method="yake") == "yake"
        assert phrase_channel({"channel": "tfidf", "score": 1.5}) == "tfidf"
        assert phrase_channel({"channel": "proper", "score": 1.5}) == "uppercase"

    def test_phrases_terms_splits_channel_scores(self, temp_dir: Path) -> None:
        papers = [
            {
                "paper_id": "p1",
                "source": "extracted",
                "text_source": "xml-body",
                "phrases": [
                    {
                        "phrase": "north atlantic",
                        "display": "North Atlantic",
                        "score": 2.0,
                        "channel": "uppercase",
                    },
                    {
                        "phrase": "opal",
                        "display": "opal",
                        "score": 0.04,
                        "channel": "tfidf",
                    },
                ],
            },
            {
                "paper_id": "p2",
                "source": "extracted",
                "text_source": "xml-body",
                "phrases": [
                    {
                        "phrase": "north atlantic",
                        "display": "North Atlantic",
                        "score": 1.5,
                        "channel": "uppercase",
                    },
                    {
                        "phrase": "north atlantic",
                        "display": "North Atlantic",
                        "score": 0.05,
                        "channel": "tfidf",
                    },
                ],
            },
        ]
        _, terms_path = write_phrases_summary_csv(
            temp_dir, papers, score_higher_is_better=True, method="tfidf"
        )
        import csv

        rows = {r["phrase"]: r for r in csv.DictReader(terms_path.open())}
        na = rows["north atlantic"]
        assert na["n_papers"] == "2"
        assert na["n_uppercase"] == "2"
        assert na["n_tfidf"] == "1"
        assert float(na["best_uppercase"]) == 2.0
        assert float(na["best_tfidf"]) == 0.05
        assert na["score_channel"] == "uppercase"
        assert float(na["best_score"]) == 2.0
        opal = rows["opal"]
        assert opal["n_uppercase"] == "0"
        assert opal["n_tfidf"] == "1"
        assert opal["score_channel"] == "tfidf"

    def test_tfidf_phrases_for_corpus_ranks_distinctive_terms(self) -> None:
        texts = [
            "AMOC weakening affects rainfall over the Indian Ocean near India.",
            "Arctic sea ice variability drives Atlantic overturning changes.",
            "Coral reefs bleach during marine heatwaves in the Pacific.",
        ]
        rows = tfidf_phrases_for_corpus(texts, n=3, top=10)
        assert len(rows) == 3
        first = {p["phrase"] for p in rows[0]}
        assert "amoc" in first or "rainfall" in first or "indian" in first
        # Scores are TF-IDF weights (higher = better)
        assert rows[0][0]["score"] >= rows[0][-1]["score"]

    def test_proper_phrases_from_text_finds_indian_ocean(self) -> None:
        text = (
            "Impacts reach the Indian Ocean basin. "
            "Further Indian Ocean warming affects India and the Bay of Bengal. "
            "The Indian Ocean signal persists."
        )
        phrases = {p["phrase"] for p in proper_phrases_from_text(text, min_count=2)}
        assert "indian ocean" in phrases

    def test_extract_plain_text_from_xml_body(self, temp_dir: Path) -> None:
        xml_path = Path(temp_dir, "paper.xml")
        xml_path.write_text(
            """<?xml version="1.0"?>
            <article>
              <front><article-meta>
                <title-group><article-title>AMOC and monsoon</article-title></title-group>
                <abstract><p>Abstract mentions climate only.</p></abstract>
              </article-meta></front>
              <body><sec><title>Results</title>
                <p>Rainfall over the Indian Ocean near India declines.</p>
              </sec>
              <sec><title>References</title>
                <p>Should not appear in indexed body text.</p>
              </sec></body>
              <back><ref-list><ref><p>Also skip back references.</p></ref></ref-list></back>
            </article>
            """,
            encoding="utf-8",
        )
        bits = extract_plain_text_from_xml(xml_path)
        assert "AMOC" in bits["title"]
        assert "climate" in bits["abstract"]
        assert "Indian Ocean" in bits["body"]
        assert "India" in bits["body"]
        assert "Should not appear" not in bits["body"]
        assert "Also skip back" not in bits["body"]

    def test_build_phrase_input_defaults_to_body_only(self, temp_dir: Path) -> None:
        from semantic_corpus.cluster_review.step2 import build_phrase_input_text

        xml_path = Path(temp_dir, "PMC1.xml")
        xml_path.write_text(
            """<?xml version="1.0"?>
            <article>
              <front><article-meta>
                <title-group><article-title>Front Title India</article-title></title-group>
                <abstract><p>Abstract India only.</p></abstract>
              </article-meta></front>
              <body><sec><p>Body mentions Indian Ocean clearly.</p></sec></body>
            </article>
            """,
            encoding="utf-8",
        )
        # Simulate bag layout find_paper_xml expects
        bag = Path(temp_dir, "bag")
        xml_dir = Path(bag, "data", "documents", "xml")
        xml_dir.mkdir(parents=True)
        xml_path.rename(Path(xml_dir, "PMC1.xml"))
        built = build_phrase_input_text(
            {"title": "Front Title India", "abstract": "Abstract India only."},
            bag_root=bag,
            paper_id="PMC1",
            include_xml_body=True,
            include_front_matter=False,
        )
        assert "Indian Ocean" in built["text"]
        assert "Abstract India" not in built["text"]
        assert "Front Title" not in built["text"]
        assert built["text_source"] == "xml-body"


class TestExtractYakePhrases:
    def test_extract_and_cache(
        self, mini_bagit: Path, fake_extractor: FakeYakeExtractor
    ) -> None:
        summary = extract_yake_phrases(
            mini_bagit, n=3, top=10, force=True, extractor=fake_extractor
        )
        assert summary["step"] == 2
        assert summary["params"]["method"] == "yake"
        assert summary["paper_count"] == 2
        assert summary["papers_extracted"] == 2
        assert summary["total_phrase_mentions"] > 0
        assert Path(summary["phrases_dir"]).is_dir()
        assert Path(summary["index_path"]).is_file()
        assert Path(summary["phrases_csv"]).is_file()
        assert Path(summary["phrases_summary_csv"]).is_file()
        assert Path(summary["phrases_terms_csv"]).is_file()

        detail = Path(summary["phrases_csv"]).read_text(encoding="utf-8")
        assert "paper_id,rank,phrase,display,score,channel,source" in detail
        assert "marine heatwaves" in detail

        paper_summary = Path(summary["phrases_summary_csv"]).read_text(encoding="utf-8")
        assert "paper_id,phrase_count,top_phrases" in paper_summary

        terms = Path(summary["phrases_terms_csv"]).read_text(encoding="utf-8")
        assert (
            "best_uppercase,n_uppercase,best_tfidf,n_tfidf,best_yake,n_yake"
            in terms
        )
        assert "best_score,score_channel,paper_ids" in terms
        assert "yake" in terms

        for paper in summary["papers"]:
            assert paper["source"] == "extracted"
            assert Path(paper["cache_path"]).is_file()
            cached = load_cached_phrases(Path(paper["cache_path"]))
            assert cached is not None
            assert cached["params"]["n"] == 3
            assert cached["params"]["method"] == "yake"
            assert cached["params"]["phrase_schema"] == PHRASE_SCHEMA
            assert all(p.get("channel") == "yake" for p in cached["phrases"])

    def test_uses_cache_on_second_run(
        self, mini_bagit: Path, fake_extractor: FakeYakeExtractor
    ) -> None:
        extract_yake_phrases(mini_bagit, force=True, extractor=fake_extractor)
        second = extract_yake_phrases(mini_bagit, use_cache=True, force=False)
        assert second["papers_from_cache"] == 2
        assert second["papers_extracted"] == 0
        assert all(p["source"] == "cache" for p in second["papers"])

    def test_find_phrase_cache(
        self, mini_bagit: Path, fake_extractor: FakeYakeExtractor
    ) -> None:
        status = find_phrase_cache(mini_bagit, ["nope"])
        assert status["missing_count"] == 1
        extract_yake_phrases(mini_bagit, force=True, extractor=fake_extractor)
        bag = json.loads(
            Path(mini_bagit, "phrases", "index.json").read_text(encoding="utf-8")
        )
        status2 = find_phrase_cache(mini_bagit, bag["paper_ids"])
        assert status2["ready"] is True
        assert status2["cached_count"] == 2

    def test_phrases_dir_beside_corpus(self, mini_bagit: Path) -> None:
        assert phrases_dir_for_corpus(mini_bagit) == Path(mini_bagit, "phrases")

    def test_missing_corpus(self, temp_dir: Path) -> None:
        with pytest.raises(CorpusError):
            extract_yake_phrases(Path(temp_dir, "missing"))

    def test_clear_all_caches(
        self, mini_bagit: Path, fake_extractor: FakeYakeExtractor
    ) -> None:
        first = extract_yake_phrases(
            mini_bagit, force=True, extractor=fake_extractor
        )
        phrases_dir = Path(first["phrases_dir"])
        assert phrases_dir.is_dir()
        assert list(phrases_dir.glob("*.json"))

        cleared = clear_all_caches(mini_bagit)
        assert cleared["cleared"] is True
        assert cleared["deleted_count"] >= 3  # 2 papers + index
        assert not phrases_dir.exists()

        status = find_phrase_cache(mini_bagit, first["paper_ids"])
        assert status["ready"] is False
        assert status["cached_count"] == 0

        again = clear_all_caches(mini_bagit)
        assert again["deleted_count"] == 0
        assert again["cleared"] is True


class TestExtractTfidfPhrases:
    def test_default_extract_phrases_uses_tfidf(self, mini_bagit: Path) -> None:
        pytest.importorskip("sklearn")
        summary = extract_phrases(mini_bagit, force=True, n=3, top=10)
        assert summary["params"]["method"] == "tfidf"
        assert summary["params"]["phrase_schema"] == PHRASE_SCHEMA
        assert summary["paper_count"] == 2
        assert summary["papers_extracted"] == 2
        assert Path(summary["phrases_csv"]).is_file()
        channels = {
            p.get("channel")
            for paper in summary["papers"]
            for p in paper["phrases"]
        }
        assert channels <= {"uppercase", "tfidf"}
        assert "uppercase" in channels or "tfidf" in channels
        terms_header = Path(summary["phrases_terms_csv"]).read_text(
            encoding="utf-8"
        ).splitlines()[0]
        assert "best_uppercase" in terms_header and "score_channel" in terms_header

    def test_tfidf_cache_roundtrip(self, mini_bagit: Path) -> None:
        pytest.importorskip("sklearn")
        extract_tfidf_phrases(mini_bagit, force=True, top=10)
        second = extract_tfidf_phrases(
            mini_bagit, use_cache=True, force=False, top=10
        )
        assert second["papers_from_cache"] == 2
        assert second["papers_extracted"] == 0

    def test_xml_body_surfaces_india_without_seeds(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("sklearn")

        def _search_with_india_body(
            *,
            query_string: str,
            repository: str,
            limit: int,
            output_dir: Path,
            formats,
            start_date: str = None,
            end_date: str = None,
        ):
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            papers = [
                (
                    "PMC8000001",
                    "AMOC variability",
                    "We study Atlantic overturning circulation.",
                    "Impacts reach the Indian Ocean basin and monsoon rainfall over India.",
                ),
                (
                    "PMC8000002",
                    "Arctic sea ice",
                    "Sea ice anomalies in the Arctic Ocean.",
                    "Polar amplification changes winter storm tracks over Europe.",
                ),
                (
                    "PMC8000003",
                    "Pacific coral bleaching",
                    "Marine heatwaves bleach coral reefs.",
                    "Thermal stress rises across tropical Pacific reef systems.",
                ),
            ]
            results = []
            for pmcid, title, abstract, body in papers[:limit]:
                Path(output_dir, f"{pmcid}.xml").write_text(
                    f"""<?xml version="1.0"?>
                    <article>
                      <front><article-meta>
                        <title-group><article-title>{title}</article-title></title-group>
                        <abstract><p>{abstract}</p></abstract>
                      </article-meta></front>
                      <body><sec><p>{body}</p></sec></body>
                    </article>
                    """,
                    encoding="utf-8",
                )
                results.append(
                    {
                        "pmcid": pmcid,
                        "title": title,
                        "abstract": abstract,
                        "authors": [{"fullName": "Tester"}],
                        "publication_date": "2024-01-01",
                    }
                )
            return results, len(results)

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.step0.run_repository_search",
            _search_with_india_body,
        )
        corpus_dir = Path(temp_dir, "corpora", "india_body")
        create_corpus_from_query(
            query_string="AMOC AND India",
            query_name="india_body",
            query_dir=Path(temp_dir, "queries", "india_body"),
            limit=3,
            formats=["xml"],
            corpus_dir=corpus_dir,
            create_bagit=True,
        )
        summary = extract_tfidf_phrases(
            corpus_dir,
            force=True,
            include_xml_body=True,
            top=15,
            n=3,
        )
        assert summary["paper_count"] == 3
        first = next(p for p in summary["papers"] if "8000001" in p["paper_id"])
        phrases = {p["phrase"] for p in first["phrases"]}
        assert "india" in phrases or "indian ocean" in phrases
        assert "xml-body" in (first.get("text_source") or "")
