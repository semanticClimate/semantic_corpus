import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import (
    handle_from_uchile_url,
    id_from_uchile_url,
)
from semantic_corpus.repositories.uchile import UchileRepository


class TestUchileRepository(unittest.TestCase):
    def test_id_from_uchile_url(self) -> None:
        # Full URL
        url = "https://repositorio.uchile.cl/handle/2250/110429"
        self.assertEqual(id_from_uchile_url(url), "uchile_2250_110429")
        self.assertEqual(handle_from_uchile_url(url), "uchile_2250_110429")

        # URL with query param
        url_query = "https://repositorio.uchile.cl/handle/2250/110429?show=full"
        self.assertEqual(id_from_uchile_url(url_query), "uchile_2250_110429")

        # Raw handle
        raw_handle = "2250/110429"
        self.assertEqual(id_from_uchile_url(raw_handle), "uchile_2250_110429")

        # Handle with underscore
        raw_handle_underscore = "2250_110429"
        self.assertEqual(id_from_uchile_url(raw_handle_underscore), "uchile_2250_110429")

        # Prefixed ID
        prefixed_id = "uchile_2250_110429"
        self.assertEqual(id_from_uchile_url(prefixed_id), "uchile_2250_110429")

        # Numeric only ID
        num_id = "110429"
        self.assertEqual(id_from_uchile_url(num_id), "uchile_2250_110429")

        # Empty string
        self.assertEqual(id_from_uchile_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("uchile")
        self.assertIsInstance(repo, UchileRepository)
        self.assertIn("uchile", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = UchileRepository()
        html = """
        <html>
        <body>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/handle/2250/110429">Efecto del glifosato en suelos agricolas</a>
                </h4>
            </div>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/handle/2250/110430?show=full">Impacto ambiental de plaguicidas</a>
                </h4>
            </div>
            <div class="other">
                <a href="/browse">Explorar</a>
                <a href="/community-list">Comunidades</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://repositorio.uchile.cl/handle/2250/110429", links)
        self.assertIn("https://repositorio.uchile.cl/handle/2250/110430", links)

    def test_extract_metadata(self) -> None:
        repo = UchileRepository()
        html = """
        <html>
        <head>
            <title>Efecto del glifosato en suelos agricolas - Repositorio Académico</title>
            <meta name="citation_title" content="Efecto del glifosato en suelos agricolas" />
            <meta name="citation_author" content="González, Carlos" />
            <meta name="citation_author" content="Silva, María" />
            <meta name="citation_abstract" content="Evaluación de la persistencia de herbicidas en Chile central." />
            <meta name="citation_publication_date" content="2021" />
            <meta name="citation_journal_title" content="Tesis de Magíster - Universidad de Chile" />
            <meta name="citation_doi" content="10.5354/uchile.2021.01" />
            <meta name="citation_pdf_url" content="https://repositorio.uchile.cl/bitstream/handle/2250/110429/tesis.pdf" />
        </head>
        <body></body>
        </html>
        """
        url = "https://repositorio.uchile.cl/handle/2250/110429"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "uchile_2250_110429")
        self.assertEqual(meta["title"], "Efecto del glifosato en suelos agricolas")
        self.assertEqual(meta["authors"], ["González, Carlos", "Silva, María"])
        self.assertEqual(meta["abstract"], "Evaluación de la persistencia de herbicidas en Chile central.")
        self.assertEqual(meta["publication_date"], "2021")
        self.assertEqual(meta["journal"], "Tesis de Magíster - Universidad de Chile")
        self.assertEqual(meta["doi"], "10.5354/uchile.2021.01")
        self.assertEqual(meta["pdf_url"], "https://repositorio.uchile.cl/bitstream/handle/2250/110429/tesis.pdf")
        self.assertEqual(meta["source_repository"], "uchile")

    def test_search_papers(self) -> None:
        repo = UchileRepository()
        search_html = """
        <html><body>
            <div class="ds-artifact-item">
                <a href="/handle/2250/110429">Articulo Uchile</a>
            </div>
        </body></html>
        """
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo Uchile" />
            <meta name="citation_author" content="Autor Uchile" />
            <meta name="citation_pdf_url" content="https://repositorio.uchile.cl/paper.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str = "https://repositorio.uchile.cl/handle/2250/110429"):
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "discover" in url or "simple-search" in url:
                return FakeResponse(search_html)
            elif "2250/110429" in url:
                return FakeResponse(item_html)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("glifosato", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Articulo Uchile")
        self.assertEqual(results[0]["authors"], ["Autor Uchile"])

    def test_download_paper(self) -> None:
        repo = UchileRepository()
        item_html = """
        <html><head>
            <meta name="citation_title" content="Tesis Uchile" />
            <meta name="citation_pdf_url" content="https://repositorio.uchile.cl/document.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, content: bytes = b"%PDF-1.4 dummy", text: str = "", headers=None):
                self.content = content
                self.text = text
                self.url = "https://repositorio.uchile.cl/handle/2250/110429"
                self.headers = headers or {"content-type": "application/pdf"}

        def fake_get(url, params=None, timeout=30):
            if "handle" in url:
                return FakeResponse(text=item_html)
            if "document.pdf" in url:
                return FakeResponse(content=b"%PDF-1.4 simulated pdf")
            return None

        repo.http.get = MagicMock(side_effect=fake_get)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            res = repo.download_paper("uchile_2250_110429", out_dir, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((out_dir / "uchile_2250_110429_metadata.json").exists())
            self.assertTrue((out_dir / "uchile_2250_110429.pdf").exists())

    def test_get_repository_info(self) -> None:
        repo = UchileRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "UCHILE")
        self.assertEqual(info["base_url"], "https://repositorio.uchile.cl")
        self.assertIn("pdf", info["supported_formats"])


if __name__ == "__main__":
    unittest.main()
