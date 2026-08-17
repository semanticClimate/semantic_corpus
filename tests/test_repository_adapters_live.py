"""Live smoke tests for OpenAlex, SciELO, and Redalyc repository adapters."""

import json
from pathlib import Path

import pytest

from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.corpus_review.query_run import load_pilot_config
from semantic_corpus.repositories._ids import get_result_paper_id


REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"

ADAPTER_CONFIGS = {
    "openalex": CONFIG_DIR / "openalex_climate_anxiety.yaml",
    "scielo": CONFIG_DIR / "scielo_climate_change.yaml",
    "redalyc": CONFIG_DIR / "redalyc_climate_change.yaml",
}


@pytest.fixture(params=list(ADAPTER_CONFIGS.values()), ids=list(ADAPTER_CONFIGS.keys()))
def adapter_config_path(request: pytest.FixtureRequest) -> Path:
    path = request.param
    assert path.is_file(), f"Adapter config missing: {path}"
    return path


class TestAdapterConfigs:
    def test_adapter_yaml_configs_load(self, adapter_config_path: Path) -> None:
        config = load_pilot_config(adapter_config_path)
        assert config["repository"] in {"openalex", "scielo", "redalyc"}
        assert config["query_string"]
        assert config["limit"] >= 1
        assert config["formats"]


class TestOpenAlexLiveSmoke:
    @pytest.mark.live_api
    @pytest.mark.network
    def test_openalex_search_and_download(self, temp_dir: Path) -> None:
        repo = RepositoryFactory.get_repository("openalex")
        results = repo.search_papers("climate anxiety", limit=3)
        assert len(results) >= 1, "OpenAlex search should return at least one hit"
        assert results[0].get("title"), "OpenAlex result should include a title"

        paper_id = get_result_paper_id(results[0])
        assert paper_id, "OpenAlex result should expose a paper_id"

        download = repo.download_paper(paper_id, temp_dir, formats=["pdf"])
        assert download["success"] is True
        assert download["files"], "OpenAlex download should write at least metadata"
        assert any(path.endswith("_metadata.json") for path in download["files"])

    @pytest.mark.live_api
    @pytest.mark.network
    def test_run_pilot_from_openalex_config(self, temp_dir: Path, monkeypatch) -> None:
        from semantic_corpus.corpus_review import workflow

        config = load_pilot_config(ADAPTER_CONFIGS["openalex"])
        output_dir = Path(temp_dir, "queries", config["output_subdir"])

        def fake_temp_dir():
            return str(temp_dir)

        monkeypatch.setattr(workflow, "get_project_temp_dir", fake_temp_dir)

        record = workflow.run_pilot_from_config(ADAPTER_CONFIGS["openalex"])
        assert record["result_count"] >= 1
        assert Path(record["search_results_path"]).is_file()
        with open(record["search_results_path"], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert isinstance(payload, list)
        assert payload[0].get("source_repository") == "openalex"


class TestSciELOLiveSmoke:
    @pytest.mark.live_api
    @pytest.mark.network
    def test_scielo_search_and_download(self, temp_dir: Path) -> None:
        repo = RepositoryFactory.get_repository("scielo")
        results = repo.search_papers("cambio climatico", limit=3)
        assert len(results) >= 1, "SciELO search should return at least one hit"
        assert results[0].get("title"), "SciELO result should include a title"

        paper_id = get_result_paper_id(results[0])
        download = repo.download_paper(paper_id, temp_dir, formats=["html", "pdf"])
        assert download["success"] is True
        assert any(path.endswith(".html") for path in download["files"])

    @pytest.mark.live_api
    @pytest.mark.network
    def test_run_pilot_from_scielo_config(self, temp_dir: Path, monkeypatch) -> None:
        from semantic_corpus.corpus_review import workflow

        monkeypatch.setattr(workflow, "get_project_temp_dir", lambda: str(temp_dir))

        record = workflow.run_pilot_from_config(ADAPTER_CONFIGS["scielo"])
        assert record["result_count"] >= 1
        assert Path(record["search_results_path"]).is_file()


class TestRedalycLiveSmoke:
    KNOWN_ARTICLE_ID = "14075366011"

    @pytest.mark.live_api
    @pytest.mark.network
    def test_redalyc_known_article_metadata_and_download(self, temp_dir: Path) -> None:
        repo = RepositoryFactory.get_repository("redalyc")
        metadata = repo.get_paper_metadata(self.KNOWN_ARTICLE_ID)
        assert metadata.get("title"), "Redalyc metadata should include title"
        assert metadata.get("pdf_url"), "Known Redalyc article should expose PDF URL"

        download = repo.download_paper(self.KNOWN_ARTICLE_ID, temp_dir, formats=["html", "pdf"])
        assert download["success"] is True
        assert any(path.endswith(".pdf") for path in download["files"])

    @pytest.mark.live_api
    @pytest.mark.network
    def test_redalyc_search_best_effort(self) -> None:
        repo = RepositoryFactory.get_repository("redalyc")
        results = repo.search_papers("cambio climatico", limit=3)
        # Search may legitimately return zero when legacy endpoint is down.
        assert isinstance(results, list)
        if results:
            assert results[0].get("title")

    @pytest.mark.live_api
    @pytest.mark.network
    def test_run_pilot_from_redalyc_config(self, temp_dir: Path, monkeypatch) -> None:
        from semantic_corpus.corpus_review import workflow

        monkeypatch.setattr(workflow, "get_project_temp_dir", lambda: str(temp_dir))

        record = workflow.run_pilot_from_config(ADAPTER_CONFIGS["redalyc"])
        assert record["result_count"] >= 0
        assert Path(record["search_results_path"]).is_file()
