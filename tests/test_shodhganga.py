"""Unit tests for Shodhganga repository integration."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.monitoring.checker import build_targets
from semantic_corpus.repositories._ids import (
    handle_from_shodhganga_url,
    id_from_shodhganga_url,
)
from semantic_corpus.repositories.shodhganga import ShodhgangaRepository


class TestShodhgangaRepository(unittest.TestCase):
    def test_id_from_shodhganga_url(self) -> None:
        # Full URL
        url = "https://shodhganga.inflibnet.ac.in/handle/10603/454861"
        self.assertEqual(id_from_shodhganga_url(url), "shodhganga_10603_454861")
        self.assertEqual(handle_from_shodhganga_url(url), "shodhganga_10603_454861")

        # Handle.net URL
        hdl_url = "http://hdl.handle.net/10603/454861"
        self.assertEqual(id_from_shodhganga_url(hdl_url), "shodhganga_10603_454861")

        # Raw handle
        raw_handle = "10603/454861"
        self.assertEqual(id_from_shodhganga_url(raw_handle), "shodhganga_10603_454861")

        # Handle with underscore
        raw_handle_underscore = "10603_454861"
        self.assertEqual(
            id_from_shodhganga_url(raw_handle_underscore), "shodhganga_10603_454861"
        )

        # Prefixed ID
        prefixed_id = "shodhganga_10603_454861"
        self.assertEqual(id_from_shodhganga_url(prefixed_id), "shodhganga_10603_454861")

        # Numeric only ID
        num_id = "454861"
        self.assertEqual(id_from_shodhganga_url(num_id), "shodhganga_10603_454861")

        # Empty string
        self.assertEqual(id_from_shodhganga_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("shodhganga")
        self.assertIsInstance(repo, ShodhgangaRepository)
        self.assertIn("shodhganga", RepositoryFactory.list_repositories())

    def test_observability_monitoring_target(self) -> None:
        targets = build_targets()
        names = [t.name for t in targets]
        self.assertIn("shodhganga", names)
        shodhganga_target = next(t for t in targets if t.name == "shodhganga")
        self.assertEqual(
            shodhganga_target.url,
            "https://shodhganga.inflibnet.ac.in/browse?type=title",
        )
        self.assertIs(shodhganga_target.repository_class, ShodhgangaRepository)

    def test_extract_article_links(self) -> None:
        repo = ShodhgangaRepository()
        html = """
        <html>
        <body>
            <table class="table">
                <tr>
                    <td><a href="/handle/10603/454861">Climate modeling in India</a></td>
                </tr>
                <tr>
                    <td><a href="/handle/10603/470698">Determinants Influencing Climate</a></td>
                </tr>
            </table>
            <div>
                <a href="/browse?type=title">Browse Title</a>
                <a href="/community-list">Community</a>
                <a href="/simple-search?query=test">Search</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://shodhganga.inflibnet.ac.in/handle/10603/454861", links)
        self.assertIn("https://shodhganga.inflibnet.ac.in/handle/10603/470698", links)

    def test_extract_metadata_from_meta_tags(self) -> None:
        repo = ShodhgangaRepository()
        html = """
        <html>
        <head>
            <title>Climate modeling - Shodhganga</title>
            <meta name="DC.title" content="Climate modeling in Simulating Modulated properties" />
            <meta name="citation_title" content="Climate modeling in Simulating Modulated properties" />
            <meta name="citation_author" content="Verma, Shruti" />
            <meta name="DC.creator" content="Verma, Shruti" />
            <meta name="DC.contributor" content="Bhatla, R" />
            <meta name="citation_publisher" content="Banaras Hindu University" />
            <meta name="citation_date" content="2022" />
            <meta name="DCTERMS.abstract" content="Detailed analysis of summer monsoons in India." />
            <meta name="citation_pdf_url" content="https://shodhganga.inflibnet.ac.in/bitstream/10603/454861/1/01_title.pdf" />
            <meta name="DC.identifier" content="http://hdl.handle.net/10603/454861" />
            <meta name="citation_keywords" content="Climate; Monsoon" />
        </head>
        <body>
            <a href="/bitstream/10603/454861/1/01_title.pdf">01_title.pdf</a>
            <a href="/bitstream/10603/454861/2/chapter1.pdf">chapter1.pdf</a>
        </body>
        </html>
        """
        article_url = "https://shodhganga.inflibnet.ac.in/handle/10603/454861"
        meta = repo._extract_metadata(html, article_url)

        self.assertEqual(meta["paper_id"], "shodhganga_10603_454861")
        self.assertEqual(
            meta["title"], "Climate modeling in Simulating Modulated properties"
        )
        self.assertEqual(meta["authors"], ["Verma, Shruti"])
        self.assertEqual(meta["guides"], ["Bhatla, R"])
        self.assertEqual(meta["publisher"], "Banaras Hindu University")
        self.assertEqual(meta["publication_date"], "2022")
        self.assertEqual(
            meta["abstract"], "Detailed analysis of summer monsoons in India."
        )
        self.assertEqual(
            meta["pdf_url"],
            "https://shodhganga.inflibnet.ac.in/bitstream/10603/454861/1/01_title.pdf",
        )
        self.assertEqual(len(meta["pdf_urls"]), 2)
        self.assertEqual(meta["source_repository"], "shodhganga")

    def test_extract_metadata_fallback_to_table(self) -> None:
        repo = ShodhgangaRepository()
        html = """
        <html>
        <head>
            <title>Shodhganga@INFLIBNET: Atmospheric Sciences Thesis</title>
        </head>
        <body>
            <table class="itemDisplayTable">
                <tr><td class="metadataFieldLabel">Title:</td><td class="metadataFieldValue">Atmospheric Sciences Study</td></tr>
                <tr><td class="metadataFieldLabel">Researcher:</td><td class="metadataFieldValue">Kumar, Rajesh</td></tr>
                <tr><td class="metadataFieldLabel">Guide(s):</td><td class="metadataFieldValue">Sharma, Anil</td></tr>
                <tr><td class="metadataFieldLabel">University:</td><td class="metadataFieldValue">Delhi University</td></tr>
                <tr><td class="metadataFieldLabel">Completed Date:</td><td class="metadataFieldValue">2021</td></tr>
                <tr><td class="metadataFieldLabel">Abstract:</td><td class="metadataFieldValue">Study of tropospheric dynamics.</td></tr>
            </table>
            <a href="/bitstream/10603/12345/1/full_thesis.pdf">full_thesis.pdf</a>
        </body>
        </html>
        """
        article_url = "https://shodhganga.inflibnet.ac.in/handle/10603/12345"
        meta = repo._extract_metadata(html, article_url)

        self.assertEqual(meta["paper_id"], "shodhganga_10603_12345")
        self.assertEqual(meta["title"], "Atmospheric Sciences Study")
        self.assertEqual(meta["authors"], ["Kumar, Rajesh"])
        self.assertEqual(meta["guides"], ["Sharma, Anil"])
        self.assertEqual(meta["publisher"], "Delhi University")
        self.assertEqual(meta["publication_date"], "2021")
        self.assertEqual(meta["abstract"], "Study of tropospheric dynamics.")
        self.assertEqual(
            meta["pdf_url"],
            "https://shodhganga.inflibnet.ac.in/bitstream/10603/12345/1/full_thesis.pdf",
        )

    def test_anubis_challenge_resolution(self) -> None:
        repo = ShodhgangaRepository()

        # Mock initial response with Anubis challenge
        mock_initial = MagicMock()
        challenge_payload = {
            "challenge": {
                "id": "test-challenge-id",
                "randomData": "sample_seed_",
            },
            "rules": {"difficulty": 2},
        }
        mock_initial.text = (
            f'<html><script id="anubis_challenge" type="application/json">'
            f"{json.dumps(challenge_payload)}</script></html>"
        )
        mock_initial.request = MagicMock(path_url="/handle/10603/454861")

        mock_passed = MagicMock()
        mock_passed.text = "<html><body>Real Content After Challenge</body></html>"

        repo.http.get = MagicMock(return_value=mock_initial)
        repo.http.session.get = MagicMock(return_value=mock_passed)

        resp = repo._get_with_anubis("https://shodhganga.inflibnet.ac.in/test")

        self.assertIsNotNone(resp)
        self.assertEqual(resp.text, mock_passed.text)
        # Verify pass-challenge call was made
        repo.http.session.get.assert_called_once()
        called_url = repo.http.session.get.call_args[0][0]
        self.assertIn("/.within.website/x/cmd/anubis/api/pass-challenge", called_url)
        self.assertIn("id=test-challenge-id", called_url)

    def test_search_papers(self) -> None:
        repo = ShodhgangaRepository()

        search_html = """
        <html><body>
            <a href="/handle/10603/454861">Title 1</a>
        </body></html>
        """
        item_html = """
        <html>
        <head>
            <meta name="DC.title" content="Climate Impact" />
            <meta name="DC.creator" content="Researcher Name" />
        </head>
        </html>
        """

        mock_search_resp = MagicMock(text=search_html)
        mock_item_resp = MagicMock(text=item_html)

        def mock_get(url: str, **kwargs):
            if "simple-search" in url:
                return mock_search_resp
            return mock_item_resp

        repo._get_with_anubis = MagicMock(side_effect=mock_get)

        results = repo.search_papers("climate", limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Climate Impact")
        self.assertEqual(results[0]["authors"], ["Researcher Name"])
        self.assertEqual(results[0]["paper_id"], "shodhganga_10603_454861")

    def test_download_paper(self) -> None:
        repo = ShodhgangaRepository()

        item_html = """
        <html>
        <head>
            <meta name="DC.title" content="Thesis Download Test" />
            <meta name="DC.creator" content="Author A" />
            <meta name="citation_pdf_url" content="https://shodhganga.inflibnet.ac.in/bitstream/10603/454861/1/thesis.pdf" />
        </head>
        </html>
        """
        mock_item_resp = MagicMock(
            text=item_html,
            url="https://shodhganga.inflibnet.ac.in/handle/10603/454861",
        )

        mock_pdf_resp = MagicMock(
            content=b"%PDF-1.4 test binary pdf content",
            headers={"content-type": "application/pdf"},
        )

        def mock_get(url: str, **kwargs):
            if "handle" in url:
                return mock_item_resp
            if "bitstream" in url:
                # Ensure Referer header was passed
                headers = kwargs.get("headers", {})
                self.assertIn("Referer", headers)
                self.assertEqual(
                    headers["Referer"],
                    "https://shodhganga.inflibnet.ac.in/handle/10603/454861",
                )
                return mock_pdf_resp
            return None

        repo._get_with_anubis = MagicMock(side_effect=mock_get)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            result = repo.download_paper(
                "shodhganga_10603_454861", out_dir, formats=["pdf"]
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["paper_id"], "shodhganga_10603_454861")
            self.assertTrue(
                (out_dir / "shodhganga_10603_454861_metadata.json").exists()
            )
            self.assertTrue((out_dir / "shodhganga_10603_454861.pdf").exists())

            # Verify downloaded PDF content
            pdf_bytes = (out_dir / "shodhganga_10603_454861.pdf").read_bytes()
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_get_repository_info(self) -> None:
        repo = ShodhgangaRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "SHODHGANGA")
        self.assertEqual(info["base_url"], "https://shodhganga.inflibnet.ac.in")
        self.assertEqual(
            info["browse_url"], "https://shodhganga.inflibnet.ac.in/browse?type=title"
        )
        self.assertIn("pdf", info["supported_formats"])
        self.assertIn("metadata", info["supported_formats"])
