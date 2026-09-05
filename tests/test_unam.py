import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import (
    handle_from_unam_url,
    id_from_unam_url,
)
from semantic_corpus.repositories.unam import UnamRepository


class TestUnamRepository(unittest.TestCase):
    def test_id_from_unam_url(self) -> None:
        # Canonical URL
        url = "https://repositorio.unam.mx/contenidos/45182"
        self.assertEqual(id_from_unam_url(url), "unam_45182")
        self.assertEqual(handle_from_unam_url(url), "unam_45182")

        # Ficha URL with slug
        url_ficha = "https://repositorio.unam.mx/contenidos/ficha/clima-escolar-y-clima-familiar-45182"
        self.assertEqual(id_from_unam_url(url_ficha), "unam_45182")

        # URL with query param
        url_query = "https://repositorio.unam.mx/contenidos/45182?c=pQ8wXB&d=false"
        self.assertEqual(id_from_unam_url(url_query), "unam_45182")

        # Handle format
        url_handle = "http://hdl.handle.net/20.500.12525/45182"
        self.assertEqual(id_from_unam_url(url_handle), "unam_20_500_12525_45182")

        # Prefixed ID
        prefixed_id = "unam_45182"
        self.assertEqual(id_from_unam_url(prefixed_id), "unam_45182")

        # Numeric only ID
        num_id = "45182"
        self.assertEqual(id_from_unam_url(num_id), "unam_45182")

        # Empty string
        self.assertEqual(id_from_unam_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("unam_mexico")
        self.assertIsInstance(repo, UnamRepository)
        self.assertIn("unam_mexico", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = UnamRepository()
        html = """
        <html>
        <body>
            <div data-id="45182" class="doc-element-grid card-rel data-record-ind">
                <a class="cont-text-title-record-min" href="/contenidos/ficha/clima-escolar-45182">Clima Escolar</a>
            </div>
            <div data-id="45183" class="doc-element-grid card-rel data-record-ind">
                <a class="cont-text-title-record-min" href="/contenidos/ficha/impacto-ambiental-45183">Impacto Ambiental</a>
            </div>
            <div class="other">
                <a href="/normatividad">Normatividad</a>
                <a href="/directorio">Directorio</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://repositorio.unam.mx/contenidos/45182", links)
        self.assertIn("https://repositorio.unam.mx/contenidos/45183", links)

    def test_extract_metadata(self) -> None:
        repo = UnamRepository()
        html = """
        <html>
        <head>
            <title>CLIMA ESCOLAR Y CLIMA FAMILIAR - Repositorio Institucional de la UNAM</title>
            <meta name="citation_title" content="CLIMA ESCOLAR Y CLIMA FAMILIAR" />
            <meta name="citation_author" content="López Pérez, Mistli Guillermina" />
            <meta name="citation_abstract" content="Este estudio tuvo como objetivos conocer el efecto de genero..." />
            <meta name="citation_publication_date" content="2016-12-07" />
            <meta name="citation_journal_title" content="Revista Electrónica de Psicología Iztacala" />
            <meta name="citation_doi" content="10.1234/unam.2016.01" />
            <meta name="citation_pdf_url" content="https://www.revistas.unam.mx/article.pdf" />
        </head>
        <body>
            <p><strong>dor_id:</strong> 45182</p>
            <p><strong>245.1.0.a:</strong> CLIMA ESCOLAR Y CLIMA FAMILIAR</p>
            <p><strong>100.1.#.a:</strong> López Pérez, Mistli Guillermina</p>
            <p><strong>520.3.#.a:</strong> Este estudio tuvo como objetivos conocer el efecto de genero...</p>
            <p><strong>264.#.1.c:</strong> 2016-12-07</p>
            <p><strong>773.1.#.t:</strong> Revista Electrónica de Psicología Iztacala</p>
            <p><strong>856.4.0.u:</strong> https://www.revistas.unam.mx/article.pdf</p>
        </body>
        </html>
        """
        url = "https://repositorio.unam.mx/contenidos/45182"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "unam_45182")
        self.assertEqual(meta["title"], "CLIMA ESCOLAR Y CLIMA FAMILIAR")
        self.assertEqual(meta["authors"], ["López Pérez, Mistli Guillermina"])
        self.assertEqual(meta["abstract"], "Este estudio tuvo como objetivos conocer el efecto de genero...")
        self.assertEqual(meta["publication_date"], "2016-12-07")
        self.assertEqual(meta["journal"], "Revista Electrónica de Psicología Iztacala")
        self.assertEqual(meta["doi"], "10.1234/unam.2016.01")
        self.assertEqual(meta["pdf_url"], "https://www.revistas.unam.mx/article.pdf")
        self.assertEqual(meta["source_repository"], "unam")

    def test_search_papers(self) -> None:
        repo = UnamRepository()
        search_html = """
        <html><body>
            <div data-id="45182" class="doc-element-grid">
                <a class="cont-text-title-record-min" href="/contenidos/45182">Articulo UNAM</a>
            </div>
        </body></html>
        """
        item_html = """
        <html><head>
            <meta name="citation_title" content="Articulo UNAM" />
            <meta name="citation_author" content="Autor UNAM" />
            <meta name="citation_pdf_url" content="https://repositorio.unam.mx/paper.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str = "https://repositorio.unam.mx/contenidos/45182"):
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "contenidos" in url and params:
                return FakeResponse(search_html)
            elif "45182" in url:
                return FakeResponse(item_html)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("clima", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Articulo UNAM")
        self.assertEqual(results[0]["authors"], ["Autor UNAM"])

    def test_download_paper(self) -> None:
        repo = UnamRepository()
        item_html = """
        <html><head>
            <meta name="citation_title" content="Tesis UNAM" />
            <meta name="citation_pdf_url" content="https://repositorio.unam.mx/document.pdf" />
        </head><body></body></html>
        """

        class FakeResponse:
            def __init__(self, content: bytes = b"%PDF-1.4 dummy", text: str = "", headers=None):
                self.content = content
                self.text = text
                self.url = "https://repositorio.unam.mx/contenidos/45182"
                self.headers = headers or {"content-type": "application/pdf"}

        def fake_get(url, params=None, timeout=30):
            if "contenidos/45182" in url:
                return FakeResponse(text=item_html)
            if "document.pdf" in url:
                return FakeResponse(content=b"%PDF-1.4 simulated pdf")
            return None

        repo.http.get = MagicMock(side_effect=fake_get)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            res = repo.download_paper("unam_45182", out_dir, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((out_dir / "unam_45182_metadata.json").exists())
            self.assertTrue((out_dir / "unam_45182.pdf").exists())

    def test_get_repository_info(self) -> None:
        repo = UnamRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "UNAM")
        self.assertEqual(info["base_url"], "https://repositorio.unam.mx")
        self.assertIn("pdf", info["supported_formats"])


if __name__ == "__main__":
    unittest.main()
