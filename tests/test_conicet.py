import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import handle_from_conicet_url
from semantic_corpus.repositories.conicet import ConicetRepository


class TestConicetRepository(unittest.TestCase):
    def test_handle_from_conicet_url(self) -> None:
        url = "https://ri.conicet.gov.ar/handle/11336/183921"
        self.assertEqual(handle_from_conicet_url(url), "conicet_11336_183921")

        raw_handle = "11336/183921"
        self.assertEqual(handle_from_conicet_url(raw_handle), "conicet_11336_183921")

        prefixed_id = "conicet_11336_183921"
        self.assertEqual(handle_from_conicet_url(prefixed_id), "conicet_11336_183921")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("conicet")
        self.assertIsInstance(repo, ConicetRepository)
        self.assertIn("conicet", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = ConicetRepository()
        html = """
        <html>
        <body>
            <div class="list-item">
                <a href="/handle/11336/183921">Cambio climatico en los Andes</a>
            </div>
            <div class="list-item">
                <a href="/handle/11336/99999">Glaciares y recursos hidricos</a>
            </div>
            <div class="other">
                <a href="/browse">Explorar</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://ri.conicet.gov.ar/handle/11336/183921", links)
        self.assertIn("https://ri.conicet.gov.ar/handle/11336/99999", links)

    def test_extract_metadata(self) -> None:
        repo = ConicetRepository()
        html = """
        <html>
        <head>
            <title>Cambio climatico en los Andes - CONICET Digital</title>
            <meta name="citation_title" content="Cambio climatico en los Andes" />
            <meta name="citation_author" content="Perez, Juan" />
            <meta name="citation_author" content="Gomez, Ana" />
            <meta name="citation_abstract" content="Estudio sobre el impacto del clima." />
            <meta name="citation_publication_date" content="2023-05-12" />
            <meta name="citation_journal_title" content="Revista Argentina de Clima" />
            <meta name="citation_doi" content="10.1234/conicet.2023.01" />
            <meta name="citation_pdf_url" content="https://ri.conicet.gov.ar/bitstream/handle/11336/183921/paper.pdf" />
        </head>
        <body></body>
        </html>
        """
        url = "https://ri.conicet.gov.ar/handle/11336/183921"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "conicet_11336_183921")
        self.assertEqual(meta["title"], "Cambio climatico en los Andes")
        self.assertEqual(meta["authors"], ["Perez, Juan", "Gomez, Ana"])
        self.assertEqual(meta["abstract"], "Estudio sobre el impacto del clima.")
        self.assertEqual(meta["publication_date"], "2023-05-12")
        self.assertEqual(meta["journal"], "Revista Argentina de Clima")
        self.assertEqual(meta["doi"], "10.1234/conicet.2023.01")
        self.assertEqual(meta["pdf_url"], "https://ri.conicet.gov.ar/bitstream/handle/11336/183921/paper.pdf")
        self.assertEqual(meta["source_repository"], "conicet")

    def test_search_papers(self) -> None:
        repo = ConicetRepository()
        search_html = """
        <html><body>
            <a href="/handle/11336/183921">Articulo 1</a>
        </body></html>
        """
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo 1" />
            <meta name="citation_author" content="Autor Uno" />
            <meta name="citation_pdf_url" content="https://ri.conicet.gov.ar/paper.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, text: str):
                self.text = text
                self.url = "https://ri.conicet.gov.ar/handle/11336/183921"

        def fake_get(url, params=None, timeout=30):
            if "discover" in url or "simple-search" in url:
                return FakeResponse(search_html)
            if "11336/183921" in url:
                return FakeResponse(item_html)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("glaciares", limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Articulo 1")
        self.assertEqual(results[0]["paper_id"], "conicet_11336_183921")

    def test_download_paper(self) -> None:
        repo = ConicetRepository()
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo Descarga" />
            <meta name="citation_author" content="Autor Dos" />
            <meta name="citation_pdf_url" content="https://ri.conicet.gov.ar/download.pdf" />
        </head><body></body></html>
        """

        class FakeHtmlResponse:
            text = item_html
            url = "https://ri.conicet.gov.ar/handle/11336/183921"

        class FakePdfResponse:
            content = b"%PDF-1.4 test data"
            headers = {"content-type": "application/pdf"}

        def fake_get(url, params=None, timeout=30):
            if "handle" in url:
                return FakeHtmlResponse()
            if "download.pdf" in url:
                return FakePdfResponse()
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            res = repo.download_paper("conicet_11336_183921", tmp_path, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((tmp_path / "conicet_11336_183921_metadata.json").exists())
            self.assertTrue((tmp_path / "conicet_11336_183921.pdf").exists())

            saved_json = json.loads((tmp_path / "conicet_11336_183921_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_json["title"], "Articulo Descarga")

    def test_get_repository_info(self) -> None:
        repo = ConicetRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "CONICET")
        self.assertIn("ri.conicet.gov.ar", info["base_url"])


if __name__ == "__main__":
    unittest.main()
