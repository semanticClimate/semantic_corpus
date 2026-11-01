"""Tests for Europe PMC error interpretation (503, errCode, null wrapper)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.repositories.europe_pmc import (
    EuropePMCRepository,
    interpret_epmc_error,
    normalize_epmc_search_payload,
    _parse_epmc_response,
)


class TestInterpretEpmcError:
    def test_503_hint(self) -> None:
        msg = interpret_epmc_error(
            status_code=503,
            err_code=503,
            err_msg="Search service is temporarily unavailable. Please retry later.",
        )
        assert "503" in msg
        assert "temporarily unavailable" in msg
        assert "retry later" in msg.lower()

    def test_null_wrapper_message(self) -> None:
        msg = interpret_epmc_error(
            err_msg="responseWrapper is null (pygetpapers-style KeyError cause)"
        )
        assert "responseWrapper is null" in msg


class TestNormalizePayload:
    def test_get_shape_ok(self) -> None:
        data = normalize_epmc_search_payload(
            {"hitCount": 2, "resultList": {"result": [{"title": "A"}]}}
        )
        assert data["hitCount"] == 2

    def test_unwrap_response_wrapper(self) -> None:
        data = normalize_epmc_search_payload(
            {
                "responseWrapper": {
                    "hitCount": 1,
                    "resultList": {"result": [{"pmcid": "PMC1"}]},
                }
            }
        )
        assert data["hitCount"] == 1

    def test_err_code_payload(self) -> None:
        with pytest.raises(RepositoryError, match="503"):
            normalize_epmc_search_payload(
                {
                    "errCode": 503,
                    "errMsg": "Search service is temporarily unavailable. Please retry later.",
                }
            )

    def test_null_response_wrapper(self) -> None:
        with pytest.raises(RepositoryError, match="responseWrapper is null"):
            normalize_epmc_search_payload({"responseWrapper": None})

    def test_null_body(self) -> None:
        with pytest.raises(RepositoryError, match="empty JSON"):
            normalize_epmc_search_payload(None)

    def test_both_hitcount_and_resultlist_null(self) -> None:
        with pytest.raises(RepositoryError, match="both null"):
            normalize_epmc_search_payload({"hitCount": None, "resultList": None})


class TestParseResponse:
    def test_http_503_with_json_body(self) -> None:
        response = MagicMock()
        response.status_code = 503
        response.text = '{"errCode":503,"errMsg":"Search service is temporarily unavailable. Please retry later."}'
        response.json.return_value = {
            "errCode": 503,
            "errMsg": "Search service is temporarily unavailable. Please retry later.",
        }
        with pytest.raises(RepositoryError, match="temporarily unavailable"):
            _parse_epmc_response(response)

    def test_http_200_success(self) -> None:
        response = MagicMock()
        response.status_code = 200
        response.text = "{}"
        response.json.return_value = {
            "hitCount": 0,
            "resultList": {"result": []},
        }
        data = _parse_epmc_response(response)
        assert data["hitCount"] == 0


class TestSearchPapersErrors:
    def test_search_propagates_503(self, monkeypatch) -> None:
        repo = EuropePMCRepository()

        class FakeResponse:
            status_code = 503
            text = '{"errCode":503,"errMsg":"Search service is temporarily unavailable. Please retry later."}'

            def json(self):
                return {
                    "errCode": 503,
                    "errMsg": "Search service is temporarily unavailable. Please retry later.",
                }

        monkeypatch.setattr(
            "semantic_corpus.repositories.europe_pmc.requests.get",
            lambda *a, **k: FakeResponse(),
        )
        with pytest.raises(RepositoryError, match="503"):
            repo.search_papers("AMOC AND India", limit=5)

    def test_empty_query(self) -> None:
        repo = EuropePMCRepository()
        with pytest.raises(RepositoryError, match="non-empty query"):
            repo.search_papers("  ", limit=5)
