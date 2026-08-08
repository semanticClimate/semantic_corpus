"""Tests for review viewer HTTP server."""

import json
from pathlib import Path

import pytest

from semantic_corpus.corpus_review.interactive_review import ReviewSessionConfig
from semantic_corpus.corpus_review.review_viewer_server import ReviewViewerServer, infer_corpus_dir


def _sample_row(**overrides):
    row = {
        "review_status": "review",
        "score": 0,
        "paper_id": "europe_pmc_PMC1",
        "pmcid": "PMC1",
        "pmid": "",
        "doi": "",
        "title": "Sample paper",
        "publication_date": "2026-01-01",
        "journal": "",
        "authors": "A Author",
        "has_xml": True,
        "has_pdf": True,
        "query_name": "test",
        "query_string": "test",
        "location_terms": "",
        "pollutant_terms": "",
        "health_terms": "",
        "abstract_snippet": "Short abstract.",
        "review_notes": "",
    }
    row.update(overrides)
    return row


class TestReviewViewerServer:
    def test_resolve_document_from_query_dir(self, tmp_path: Path) -> None:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        query_dir = tmp_path / "query"
        query_dir.mkdir()
        pdf = query_dir / "PMC1.pdf"
        pdf.write_bytes(b"%PDF-sample")

        review_table = review_dir / "review_table.json"
        review_table.write_text(json.dumps([_sample_row()]), encoding="utf-8")

        config = ReviewSessionConfig(
            review_table_path=review_table,
            query_dir=query_dir,
        )
        server = ReviewViewerServer(
            review_dir=review_dir,
            review_table_path=review_table,
            session_config=config,
        )
        resolved = server._resolve_document("PMC1.pdf")
        assert resolved == pdf.resolve()

    def test_resolve_document_rejects_unsafe_paths(self, tmp_path: Path) -> None:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_table = review_dir / "review_table.json"
        review_table.write_text("[]", encoding="utf-8")
        server = ReviewViewerServer(
            review_dir=review_dir,
            review_table_path=review_table,
        )
        assert server._resolve_document("../secret.pdf") is None
        assert server._resolve_document("bad.exe") is None

    def test_health_endpoint(self, tmp_path: Path) -> None:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_table = review_dir / "review_table.json"
        review_table.write_text("[]", encoding="utf-8")
        server = ReviewViewerServer(
            review_dir=review_dir,
            review_table_path=review_table,
            port=18771,
        )
        import threading
        import time
        from urllib.request import urlopen

        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.3)
        response = urlopen("http://127.0.0.1:18771/api/health")
        assert response.status == 200
        assert b'"ok": true' in response.read()
        server.shutdown()

    def test_infer_corpus_dir_from_query_name(self, tmp_path: Path) -> None:
        corpora = tmp_path / "corpora" / "demo_query"
        (corpora / "data").mkdir(parents=True)
        query_dir = tmp_path / "temp" / "queries" / "demo_query"
        query_dir.mkdir(parents=True)
        inferred = infer_corpus_dir(query_dir)
        assert inferred == corpora.resolve()

    def test_pdf_range_request(self, tmp_path: Path) -> None:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        query_dir = tmp_path / "query"
        query_dir.mkdir()
        pdf = query_dir / "PMC1.pdf"
        pdf.write_bytes(b"%PDF-1.4\n" + b"0123456789" * 20)

        review_table = review_dir / "review_table.json"
        review_table.write_text(
            json.dumps(
                [
                    {
                        "review_status": "review",
                        "score": 0,
                        "paper_id": "europe_pmc_PMC1",
                        "pmcid": "PMC1",
                        "pmid": "",
                        "doi": "",
                        "title": "Sample",
                        "publication_date": "",
                        "journal": "",
                        "authors": "",
                        "has_xml": False,
                        "has_pdf": True,
                        "query_name": "",
                        "query_string": "",
                        "location_terms": "",
                        "pollutant_terms": "",
                        "health_terms": "",
                        "abstract_snippet": "",
                        "review_notes": "",
                    }
                ]
            ),
            encoding="utf-8",
        )
        config = ReviewSessionConfig(review_table_path=review_table, query_dir=query_dir)
        server = ReviewViewerServer(
            review_dir=review_dir,
            review_table_path=review_table,
            session_config=config,
            port=18769,
        )
        import threading
        import time
        from urllib.request import Request, urlopen

        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.3)
        req = Request(
            "http://127.0.0.1:18769/papers/PMC1.pdf",
            headers={"Range": "bytes=0-9"},
        )
        response = urlopen(req)
        assert response.status == 206
        assert response.headers.get("Accept-Ranges") == "bytes"
        assert response.headers.get("Content-Range", "").startswith("bytes 0-9/")
        assert len(response.read()) == 10
        server.shutdown()
