import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import (
    handle_from_unal_colombia_url,
    handle_from_unal_url,
    id_from_unal_colombia_url,
    id_from_unal_url,
)
from semantic_corpus.repositories.unal_colombia import UnalRepository


class TestUnalRepository(unittest.TestCase):
    def test_id_from_unal_colombia_url(self) -> None:
        # Full handle URL
        url = "https://repositorio.unal.edu.co/handle/unal/90677"
        self.assertEqual(id_from_unal_colombia_url(url), "unal_colombia_90677")
        self.assertEqual(handle_from_unal_colombia_url(url), "unal_colombia_90677")
        self.assertEqual(id_from_unal_url(url), "unal_colombia_90677")
        self.assertEqual(handle_from_unal_url(url), "unal_colombia_90677")

        # DSpace 7 item UUID URL
        url_uuid = "https://repositorio.unal.edu.co/items/44fc646d-bbad-4be9-b008-0147830d0039"
        self.assertEqual(id_from_unal_colombia_url(url_uuid), "unal_colombia_44fc646d-bbad-4be9-b008-0147830d0039")

        # HDL handle URL
        url_hdl = "https://hdl.handle.net/unal/90677"
        self.assertEqual(id_from_unal_colombia_url(url_hdl), "unal_colombia_90677")

        # URL with query param
        url_query = "https://repositorio.unal.edu.co/handle/unal/90677?show=full"
        self.assertEqual(id_from_unal_colombia_url(url_query), "unal_colombia_90677")

        # Raw handle
        raw_handle = "unal/90677"
        self.assertEqual(id_from_unal_colombia_url(raw_handle), "unal_colombia_90677")

        # Handle with underscore
        raw_handle_underscore = "unal_90677"
        self.assertEqual(id_from_unal_colombia_url(raw_handle_underscore), "unal_colombia_90677")

        # Already unal_colombia prefixed ID
        prefixed_id = "unal_colombia_90677"
        self.assertEqual(id_from_unal_colombia_url(prefixed_id), "unal_colombia_90677")

        # Numeric only ID
        num_id = "90677"
        self.assertEqual(id_from_unal_colombia_url(num_id), "unal_colombia_90677")

        # Empty string
        self.assertEqual(id_from_unal_colombia_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("unal_colombia")
        self.assertIsInstance(repo, UnalRepository)
        self.assertIn("unal_colombia", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = UnalRepository()
        html = """
        <html>
        <body>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/handle/unal/90677">Reflejos en el agua</a>
                </h4>
            </div>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/items/44fc646d-bbad-4be9-b008-0147830d0039">Articulo UUID</a>
                </h4>
            </div>
            <div class="other">
                <a href="/browse">Explorar</a>
                <a href="/home">Home</a>
                <a href="/community-list">Comunidades</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://repositorio.unal.edu.co/handle/unal/90677", links)
        self.assertIn("https://repositorio.unal.edu.co/items/44fc646d-bbad-4be9-b008-0147830d0039", links)

    def test_extract_metadata(self) -> None:
        repo = UnalRepository()
        html = """
        <html>
        <head>
            <title>Reflejos en el agua - Repositorio Institucional UNAL</title>
            <meta name="citation_title" content="Reflejos en el agua" />
            <meta name="citation_author" content="Murcia Betancourt, Luis Miguel" />
            <meta name="citation_abstract" content="Este estudio tuvo como objetivo caracterizar la composicion ecologica..." />
            <meta name="citation_publication_date" content="2026-06-17" />
            <meta name="citation_abstract_html_url" content="https://repositorio.unal.edu.co/handle/unal/90677" />
            <meta name="citation_publisher" content="Universidad Nacional de Colombia" />
            <meta name="citation_pdf_url" content="https://repositorio.unal.edu.co/bitstreams/3219ecf6-2903-47a3-bd3a-486db8763a02/download" />
        </head>
        <body></body>
        </html>
        """
        url = "https://repositorio.unal.edu.co/items/44fc646d-bbad-4be9-b008-0147830d0039"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "unal_colombia_90677")
        self.assertEqual(meta["title"], "Reflejos en el agua")
        self.assertEqual(meta["authors"], ["Murcia Betancourt, Luis Miguel"])
        self.assertEqual(meta["abstract"], "Este estudio tuvo como objetivo caracterizar la composicion ecologica...")
        self.assertEqual(meta["publication_date"], "2026-06-17")
        self.assertEqual(meta["journal"], "Universidad Nacional de Colombia")
        self.assertEqual(meta["pdf_url"], "https://repositorio.unal.edu.co/bitstreams/3219ecf6-2903-47a3-bd3a-486db8763a02/download")
        self.assertEqual(meta["source_repository"], "unal_colombia")

    def test_search_papers_html(self) -> None:
        repo = UnalRepository()
        search_html = """
        <html><body>
            <div class="ds-artifact-item">
                <a href="/handle/unal/90677">Articulo UNAL</a>
            </div>
        </body></html>
        """
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo UNAL" />
            <meta name="citation_author" content="Autor UNAL" />
            <meta name="citation_pdf_url" content="https://repositorio.unal.edu.co/bitstreams/123/download" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str = "https://repositorio.unal.edu.co/handle/unal/90677", headers=None):
                self.text = text
                self.url = url
                self.headers = headers or {"content-type": "text/html"}

        def fake_get(url, params=None, timeout=30):
            if "server/api" in url:
                return None
            elif "search" in url or "discover" in url or "home" in url:
                return FakeResponse(search_html)
            elif "90677" in url:
                return FakeResponse(item_html)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("agua", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Articulo UNAL")
        self.assertEqual(results[0]["authors"], ["Autor UNAL"])
        self.assertEqual(results[0]["source_repository"], "unal_colombia")

    def test_download_paper(self) -> None:
        repo = UnalRepository()
        item_html = """
        <html><head>
            <meta name="citation_title" content="Tesis UNAL" />
            <meta name="citation_pdf_url" content="https://repositorio.unal.edu.co/bitstreams/123/download" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, content: bytes = b"%PDF-1.4 dummy", text: str = "", headers=None):
                self.content = content
                self.text = text
                self.url = "https://repositorio.unal.edu.co/handle/unal/90677"
                self.headers = headers or {"content-type": "application/pdf"}

        def fake_get(url, params=None, timeout=30):
            if "handle" in url:
                return FakeResponse(text=item_html)
            if "download" in url:
                return FakeResponse(content=b"%PDF-1.4 simulated pdf")
            return None

        repo.http.get = MagicMock(side_effect=fake_get)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            res = repo.download_paper("unal_colombia_90677", out_dir, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((out_dir / "unal_colombia_90677_metadata.json").exists())
            self.assertTrue((out_dir / "unal_colombia_90677.pdf").exists())

    def test_get_repository_info(self) -> None:
        repo = UnalRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "unal_colombia")
        self.assertEqual(info["base_url"], "https://repositorio.unal.edu.co")
        self.assertEqual(info["home_url"], "https://repositorio.unal.edu.co/home")
        self.assertIn("pdf", info["supported_formats"])


if __name__ == "__main__":
    unittest.main()
