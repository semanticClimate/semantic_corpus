import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import id_from_uba_url
from semantic_corpus.repositories.uba import UbaRepository


class TestUbaRepository(unittest.TestCase):
    def test_id_from_uba_url(self) -> None:
        # Exactas URL
        url_exactas = "https://bibliotecadigital.exactas.uba.ar/collection/tesis/document/tesis_n5582_DiFiori"
        self.assertEqual(
            id_from_uba_url(url_exactas),
            "uba_exactas_tesis_tesis_n5582_DiFiori",
        )

        # FAUBA URL
        url_fauba = "https://ri.agro.uba.ar/greenstone3/library/collection/ti/document/cd620"
        self.assertEqual(
            id_from_uba_url(url_fauba),
            "uba_fauba_ti_cd620",
        )

        # Direct / pre-sanitized ID
        direct_id = "uba_exactas_paper_123"
        self.assertEqual(
            id_from_uba_url(direct_id),
            "uba_exactas_paper_123",
        )

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("uba")
        self.assertIsInstance(repo, UbaRepository)
        self.assertIn("uba", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = UbaRepository()
        html = """
        <html>
        <body>
            <div>
                <a href="/collection/tesis/document/tesis_n1234">Tesis 1</a>
                <a href="/collection/paper/document/paper_5678">Paper 2</a>
                <a href="/browse">Explorar</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html, "exactas")
        self.assertEqual(len(links), 2)
        self.assertIn("https://bibliotecadigital.exactas.uba.ar/collection/tesis/document/tesis_n1234", links)
        self.assertIn("https://bibliotecadigital.exactas.uba.ar/collection/paper/document/paper_5678", links)

    def test_extract_metadata_exactas(self) -> None:
        repo = UbaRepository()
        html = """
        <html>
        <head>
            <title>Efectos del herbicida glifosato</title>
            <meta name="citation_title" content="Efectos del herbicida glifosato" />
            <meta name="citation_author" content="Bartoli, Paula V." />
            <meta name="citation_author" content="Verdenelli, Romina A." />
            <meta name="citation_abstract" content="Los herbicidas pueden alterar la estructura del suelo." />
            <meta name="citation_publication_date" content="2012-04" />
            <meta name="citation_journal_title" content="Ecologia Austral" />
            <meta name="citation_doi" content="10.1234/exactas.2012.01" />
            <meta name="citation_pdf_url" content="https://bibliotecadigital.exactas.uba.ar/download/ecologiaaustral/paper.pdf" />
        </head>
        <body></body>
        </html>
        """
        url = "https://bibliotecadigital.exactas.uba.ar/collection/ecologiaaustral/document/ecologiaaustral_v022_n01_p033"
        meta = repo._extract_metadata(html, url, "exactas")
        self.assertEqual(meta["paper_id"], "uba_exactas_ecologiaaustral_ecologiaaustral_v022_n01_p033")
        self.assertEqual(meta["title"], "Efectos del herbicida glifosato")
        self.assertEqual(meta["authors"], ["Bartoli, Paula V.", "Verdenelli, Romina A."])
        self.assertEqual(meta["abstract"], "Los herbicidas pueden alterar la estructura del suelo.")
        self.assertEqual(meta["publication_date"], "2012-04")
        self.assertEqual(meta["journal"], "Ecologia Austral")
        self.assertEqual(meta["doi"], "10.1234/exactas.2012.01")
        self.assertEqual(meta["pdf_url"], "https://bibliotecadigital.exactas.uba.ar/download/ecologiaaustral/paper.pdf")
        self.assertEqual(meta["source_repository"], "uba")
        self.assertEqual(meta["faculty"], "Exactas (FCEN)")

    def test_extract_metadata_fauba(self) -> None:
        repo = UbaRepository()
        html = """
        <html>
        <head>
            <meta name="citation_title" content="Degradacion de pastizales naturales" />
            <meta name="citation_author" content="Vilarino, Hector Javier" />
            <meta name="citation_date" content="2007" />
            <meta name="citation_abstract_html_url" content="http://ri.agro.uba.ar/files/tesis.pdf" />
        </head>
        <body></body>
        </html>
        """
        url = "https://ri.agro.uba.ar/greenstone3/library/collection/ti/document/cd620"
        meta = repo._extract_metadata(html, url, "fauba")
        self.assertEqual(meta["paper_id"], "uba_fauba_ti_cd620")
        self.assertEqual(meta["title"], "Degradacion de pastizales naturales")
        self.assertEqual(meta["authors"], ["Vilarino, Hector Javier"])
        self.assertEqual(meta["publication_date"], "2007")
        self.assertEqual(meta["source_repository"], "uba")
        self.assertEqual(meta["faculty"], "FAUBA")

    def test_search_papers_combined(self) -> None:
        repo = UbaRepository()

        exactas_search_html = '<html><body><a href="/collection/tesis/document/t1">Tesis Exactas</a></body></html>'
        exactas_doc_html = '<html><head><meta name="citation_title" content="Doc Exactas"/><meta name="citation_author" content="Autor E"/></head></html>'

        fauba_search_html = '<html><body><a href="library/collection/ti/document/f1">Tesis FAUBA</a></body></html>'
        fauba_doc_html = '<html><head><meta name="citation_title" content="Doc FAUBA"/><meta name="citation_author" content="Autor F"/></head></html>'

        class FakeResponse:
            def __init__(self, text: str, url: str = ""):
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "exactas.uba.ar" in url:
                if "search" in url:
                    return FakeResponse(exactas_search_html, url)
                return FakeResponse(exactas_doc_html, url)
            elif "agro.uba.ar" in url:
                if "search" in url:
                    return FakeResponse(fauba_search_html, url)
                return FakeResponse(fauba_doc_html, url)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("glifosato", limit=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Doc Exactas")
        self.assertEqual(results[1]["title"], "Doc FAUBA")

    def test_download_paper(self) -> None:
        repo = UbaRepository()
        doc_html = """
        <html><head>
            <meta name="citation_title" content="Paper UBA" />
            <meta name="citation_author" content="Autor UBA" />
            <meta name="citation_pdf_url" content="https://bibliotecadigital.exactas.uba.ar/download/tesis/doc1.pdf" />
        </head></html>
        """

        class FakeResponse:
            def __init__(self, text: str = "", content: bytes = b"", url: str = ""):
                self.text = text
                self.content = content
                self.headers = {"content-type": "application/pdf"}
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "download" in url:
                return FakeResponse(content=b"%PDF-1.4 dummy content", url=url)
            return FakeResponse(text=doc_html, url=url)

        repo.http.get = MagicMock(side_effect=fake_get)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            res = repo.download_paper("uba_exactas_tesis_doc1", out_path, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertTrue((out_path / "uba_exactas_tesis_doc1_metadata.json").exists())
            self.assertTrue((out_path / "uba_exactas_tesis_doc1.pdf").exists())


if __name__ == "__main__":
    unittest.main()
