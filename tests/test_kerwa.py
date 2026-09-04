import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import (
    handle_from_kerwa_url,
    id_from_kerwa_url,
)
from semantic_corpus.repositories.kerwa import KerwaRepository


class TestKerwaRepository(unittest.TestCase):
    def test_id_from_kerwa_url(self) -> None:
        # Full URL
        url = "https://www.kerwa.ucr.ac.cr/handle/10669/12345"
        self.assertEqual(id_from_kerwa_url(url), "kerwa_10669_12345")
        self.assertEqual(handle_from_kerwa_url(url), "kerwa_10669_12345")

        # HDL handle URL
        url_hdl = "https://hdl.handle.net/10669/12345"
        self.assertEqual(id_from_kerwa_url(url_hdl), "kerwa_10669_12345")

        # URL with query param
        url_query = "https://www.kerwa.ucr.ac.cr/handle/10669/12345?show=full"
        self.assertEqual(id_from_kerwa_url(url_query), "kerwa_10669_12345")

        # Raw handle
        raw_handle = "10669/12345"
        self.assertEqual(id_from_kerwa_url(raw_handle), "kerwa_10669_12345")

        # Handle with underscore
        raw_handle_underscore = "10669_12345"
        self.assertEqual(id_from_kerwa_url(raw_handle_underscore), "kerwa_10669_12345")

        # Prefixed ID
        prefixed_id = "kerwa_10669_12345"
        self.assertEqual(id_from_kerwa_url(prefixed_id), "kerwa_10669_12345")

        # Numeric only ID
        num_id = "12345"
        self.assertEqual(id_from_kerwa_url(num_id), "kerwa_10669_12345")

        # Empty string
        self.assertEqual(id_from_kerwa_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("kerwa")
        self.assertIsInstance(repo, KerwaRepository)
        self.assertIn("kerwa", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = KerwaRepository()
        html = """
        <html>
        <body>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/handle/10669/12345">Uso de plaguicidas en agricultura costarricense</a>
                </h4>
            </div>
            <div class="ds-artifact-item">
                <h4 class="artifact-title">
                    <a href="/handle/10669/12346?show=full">Impacto ambiental de agroquimicos</a>
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
        self.assertIn("https://www.kerwa.ucr.ac.cr/handle/10669/12345", links)
        self.assertIn("https://www.kerwa.ucr.ac.cr/handle/10669/12346", links)

    def test_extract_metadata(self) -> None:
        repo = KerwaRepository()
        html = """
        <html>
        <head>
            <title>Uso de plaguicidas en agricultura costarricense - Kérwá</title>
            <meta name="citation_title" content="Uso de plaguicidas en agricultura costarricense" />
            <meta name="citation_author" content="Mora, Ana" />
            <meta name="citation_author" content="Vargas, Luis" />
            <meta name="citation_abstract" content="Analisis del uso y regulacion de agroquimicos en Costa Rica." />
            <meta name="citation_publication_date" content="2022" />
            <meta name="citation_journal_title" content="Tesis de Maestria - UCR" />
            <meta name="citation_doi" content="10.15517/kerwa.2022.01" />
            <meta name="citation_pdf_url" content="https://www.kerwa.ucr.ac.cr/bitstream/handle/10669/12345/tesis.pdf" />
        </head>
        <body></body>
        </html>
        """
        url = "https://www.kerwa.ucr.ac.cr/handle/10669/12345"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "kerwa_10669_12345")
        self.assertEqual(meta["title"], "Uso de plaguicidas en agricultura costarricense")
        self.assertEqual(meta["authors"], ["Mora, Ana", "Vargas, Luis"])
        self.assertEqual(meta["abstract"], "Analisis del uso y regulacion de agroquimicos en Costa Rica.")
        self.assertEqual(meta["publication_date"], "2022")
        self.assertEqual(meta["journal"], "Tesis de Maestria - UCR")
        self.assertEqual(meta["doi"], "10.15517/kerwa.2022.01")
        self.assertEqual(meta["pdf_url"], "https://www.kerwa.ucr.ac.cr/bitstream/handle/10669/12345/tesis.pdf")
        self.assertEqual(meta["source_repository"], "kerwa")

    def test_search_papers(self) -> None:
        repo = KerwaRepository()
        search_html = """
        <html><body>
            <div class="ds-artifact-item">
                <a href="/handle/10669/12345">Articulo Kerwa</a>
            </div>
        </body></html>
        """
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo Kerwa" />
            <meta name="citation_author" content="Autor UCR" />
            <meta name="citation_pdf_url" content="https://www.kerwa.ucr.ac.cr/paper.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str = "https://www.kerwa.ucr.ac.cr/handle/10669/12345"):
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "discover" in url or "simple-search" in url or "home" in url:
                return FakeResponse(search_html)
            elif "10669/12345" in url:
                return FakeResponse(item_html)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("plaguicidas", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Articulo Kerwa")
        self.assertEqual(results[0]["authors"], ["Autor UCR"])

    def test_download_paper(self) -> None:
        repo = KerwaRepository()
        item_html = """
        <html><head>
            <meta name="citation_title" content="Tesis Kerwa" />
            <meta name="citation_pdf_url" content="https://www.kerwa.ucr.ac.cr/document.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, content: bytes = b"%PDF-1.4 dummy", text: str = "", headers=None):
                self.content = content
                self.text = text
                self.url = "https://www.kerwa.ucr.ac.cr/handle/10669/12345"
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
            res = repo.download_paper("kerwa_10669_12345", out_dir, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((out_dir / "kerwa_10669_12345_metadata.json").exists())
            self.assertTrue((out_dir / "kerwa_10669_12345.pdf").exists())

    def test_get_repository_info(self) -> None:
        repo = KerwaRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "Kerwa")
        self.assertEqual(info["base_url"], "https://www.kerwa.ucr.ac.cr")
        self.assertIn("pdf", info["supported_formats"])


if __name__ == "__main__":
    unittest.main()
