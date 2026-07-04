"""Tests for additional repository adapters."""

from pathlib import Path

import pytest

from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import (
    get_result_paper_id,
    id_from_redalyc_url,
    openalex_short_id,
    pid_from_scielo_url,
    sanitize_paper_id,
)
from semantic_corpus.repositories.openalex import OpenAlexRepository
from semantic_corpus.repositories.redalyc import RedalycRepository
from semantic_corpus.repositories.scielo import SciELORepository


class TestRepositoryIds:
    def test_openalex_short_id(self) -> None:
        assert openalex_short_id("https://openalex.org/W123") == "W123"

    def test_sanitize_paper_id(self) -> None:
        assert sanitize_paper_id("10.1234/example") == "10.1234_example"

    def test_pid_from_scielo_url(self) -> None:
        url = "http://ve.scielo.org/scielo.php?script=sci_arttext&pid=S123&lang=en"
        assert pid_from_scielo_url(url) == "S123"

    def test_id_from_redalyc_url(self) -> None:
        url = "https://www.redalyc.org/articulo.oa?id=14075366011"
        assert id_from_redalyc_url(url) == "14075366011"

    def test_get_result_paper_id_prefers_explicit_field(self) -> None:
        paper = {"paper_id": "W999", "doi": "10.1/x"}
        assert get_result_paper_id(paper) == "W999"


class TestRepositoryFactory:
    def test_new_repositories_registered(self) -> None:
        repos = RepositoryFactory.list_repositories()
        assert "openalex" in repos
        assert "scielo" in repos
        assert "redalyc" in repos

    def test_get_openalex_repository(self) -> None:
        repo = RepositoryFactory.get_repository("openalex")
        assert isinstance(repo, OpenAlexRepository)

    @pytest.mark.parametrize(
        "config_name,repository",
        [
            ("openalex_climate_anxiety.yaml", "openalex"),
            ("scielo_climate_change.yaml", "scielo"),
            ("redalyc_climate_change.yaml", "redalyc"),
        ],
    )
    def test_adapter_yaml_configs(self, config_name: str, repository: str) -> None:
        from semantic_corpus.corpus_review.query_run import load_pilot_config

        config_path = Path(__file__).resolve().parent.parent / "config" / config_name
        config = load_pilot_config(config_path)
        assert config["repository"] == repository
        assert config["query_name"]
        assert config["formats"]


class TestOpenAlexRepository:
    def test_openalex_search_and_download(self, tmp_path: Path, monkeypatch) -> None:
        repo = OpenAlexRepository()

        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload
                self.content = b"%PDF-1.5"
                self.headers = {"content-type": "application/pdf"}

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        def fake_get(url, params=None, timeout=30):
            if url.endswith("/works"):
                return FakeResponse(
                    {
                        "meta": {"next_cursor": None},
                        "results": [
                            {
                                "id": "https://openalex.org/W123",
                                "doi": "https://doi.org/10.1234/test",
                                "display_name": "Climate anxiety paper",
                                "publication_date": "2024-01-01",
                                "authorships": [
                                    {"author": {"display_name": "A Author"}}
                                ],
                                "primary_location": {
                                    "source": {"display_name": "Test Journal"}
                                },
                                "best_oa_location": {
                                    "pdf_url": "https://example.org/paper.pdf"
                                },
                                "open_access": {"is_oa": True},
                                "cited_by_count": 3,
                            }
                        ],
                    }
                )
            if "/works/" in url:
                return FakeResponse(
                    {
                        "id": "https://openalex.org/W123",
                        "doi": "https://doi.org/10.1234/test",
                        "display_name": "Climate anxiety paper",
                        "publication_date": "2024-01-01",
                        "authorships": [{"author": {"display_name": "A Author"}}],
                        "primary_location": {"source": {"display_name": "Test Journal"}},
                        "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
                        "open_access": {"is_oa": True},
                        "cited_by_count": 3,
                    }
                )
            return FakeResponse(b"%PDF-1.5")

        monkeypatch.setattr("semantic_corpus.repositories.openalex.requests.get", fake_get)

        results = repo.search_papers("climate anxiety", limit=1)
        assert len(results) == 1
        assert results[0]["openalex_id"] == "W123"
        assert results[0]["doi"] == "10.1234/test"

        download = repo.download_paper("W123", tmp_path, formats=["pdf"])
        assert download["success"] is True
        assert (tmp_path / "W123.pdf").exists()
        assert (tmp_path / "W123_metadata.json").exists()


class TestSciELORepository:
    def test_scielo_extract_metadata_from_html(self) -> None:
        repo = SciELORepository()
        html = """
        <html><head>
        <meta name="citation_title" content="Climate change in Brazil"/>
        <meta name="citation_author" content="Maria Silva"/>
        <meta name="citation_pdf_url" content="https://example.org/paper.pdf"/>
        </head><body></body></html>
        """
        url = "http://ve.scielo.org/scielo.php?script=sci_arttext&pid=S123&lang=en"
        metadata = repo._extract_metadata(html, url)
        assert metadata["title"] == "Climate change in Brazil"
        assert metadata["pid"] == "S123"
        assert metadata["pdf_urls"]


class TestRedalycRepository:
    def test_redalyc_extract_metadata_from_html(self) -> None:
        repo = RedalycRepository()
        html = """
        <html><head>
        <meta name="citation_title" content="Cambio climatico"/>
        <meta name="citation_author" content="Juan Perez"/>
        <meta name="citation_pdf_url" content="https://www.redalyc.org/journal/1/1.pdf"/>
        </head><body></body></html>
        """
        url = "https://www.redalyc.org/articulo.oa?id=14075366011"
        metadata = repo._extract_metadata(html, url)
        assert metadata["title"] == "Cambio climatico"
        assert metadata["redalyc_id"] == "14075366011"
        assert metadata["pdf_url"].endswith(".pdf")

    def test_redalyc_query_match(self) -> None:
        repo = RedalycRepository()
        assert repo._query_matches({"title": "Climate change impacts"}, "climate")
        assert not repo._query_matches({"title": "Salud mental docente"}, "climate")
