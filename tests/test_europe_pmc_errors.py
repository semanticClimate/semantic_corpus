"""Tests for Europe PMC error interpretation (503, errCode, null wrapper)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.repositories.europe_pmc import (
    EuropePMCRepository,
    http_status_from_error_body,
    interpret_epmc_error,
    looks_like_fulltext_xml,
    normalize_epmc_search_payload,
    _parse_epmc_response,
)


class TestFulltextXmlGuards:
    def test_rejects_spring_boot_500_json(self) -> None:
        stub = (
            b'{"timestamp":"2026-11-08T09:14:32.370+00:00","status":500,'
            b'"error":"Internal Server Error",'
            b'"path":"/europepmc/webservices/rest/PMC13538684/fullTextXML"}'
        )
        assert looks_like_fulltext_xml(stub) is False
        assert http_status_from_error_body(stub) == 500

    def test_accepts_jats_like_xml(self) -> None:
        assert looks_like_fulltext_xml(b'<?xml version="1.0"?><article/>')
        assert looks_like_fulltext_xml(b"  <article xmlns='http://x'>x</article>")

    def test_download_refuses_json_stub(self, tmp_path, monkeypatch) -> None:
        stub = (
            b'{"timestamp":"2026-11-08T09:14:32.370+00:00","status":500,'
            b'"error":"Internal Server Error","path":"/europepmc/webservices/rest/PMC1/fullTextXML"}'
        )

        class FakeResponse:
            status_code = 200
            content = stub

            def raise_for_status(self) -> None:
                return None

        monkeypatch.setattr(
            "semantic_corpus.repositories.europe_pmc.requests.get",
            lambda *a, **k: FakeResponse(),
        )
        repo = EuropePMCRepository()
        with pytest.raises(RepositoryError, match="HTTP 500") as ei:
            repo.download_paper("PMC1", tmp_path, formats=["xml"])
        assert ei.value.status_code == 500

    def test_download_reports_http_500(self, tmp_path, monkeypatch) -> None:
        class FakeResponse:
            status_code = 500
            content = b'{"status":500,"error":"Internal Server Error"}'

            def raise_for_status(self) -> None:
                err = requests.HTTPError("500 Server Error")
                err.response = self
                raise err

        monkeypatch.setattr(
            "semantic_corpus.repositories.europe_pmc.requests.get",
            lambda *a, **k: FakeResponse(),
        )
        repo = EuropePMCRepository()
        with pytest.raises(RepositoryError, match="HTTP 500") as ei:
            repo.download_paper("PMC13538684", tmp_path, formats=["xml"])
        assert ei.value.status_code == 500


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
