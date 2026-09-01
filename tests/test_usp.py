import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.repositories._ids import id_from_usp_url
from semantic_corpus.repositories.usp import UspRepository


class TestUspRepository(unittest.TestCase):
    def test_id_from_usp_url(self) -> None:
        # Item URL
        url_item = "https://repositorio.usp.br/item/002305632"
        self.assertEqual(id_from_usp_url(url_item), "usp_002305632")

        # Direct URL
        url_direct = "https://repositorio.usp.br/direct/002305632"
        self.assertEqual(id_from_usp_url(url_direct), "usp_002305632")

        # Dedalus doc_number URL
        url_dedalus = "http://dedalus.usp.br/F/?func=direct&doc_number=002305632"
        self.assertEqual(id_from_usp_url(url_dedalus), "usp_002305632")

        # Already prefixed ID
        prefixed_id = "usp_002305632"
        self.assertEqual(id_from_usp_url(prefixed_id), "usp_002305632")

        # Raw numeric / alphanumeric ID
        raw_id = "002305632"
        self.assertEqual(id_from_usp_url(raw_id), "usp_002305632")

        # Empty string
        self.assertEqual(id_from_usp_url(""), "")

    def test_factory_registration(self) -> None:
        repo = RepositoryFactory.get_repository("usp")
        self.assertIsInstance(repo, UspRepository)
        self.assertIn("usp", RepositoryFactory.list_repositories())

    def test_extract_article_links(self) -> None:
        repo = UspRepository()
        html = """
        <html>
        <body>
            <article class="uk-article">
                <p class="uk-text-lead title-link">
                    <a class="uk-link-reset" href="item/002305632">Herbicidas em cana-de-acucar</a>
                </p>
            </article>
            <article class="uk-article">
                <p class="uk-text-lead title-link">
                    <a class="uk-link-reset" href="/item/002401928">Manejo de pragas agricolas</a>
                </p>
            </article>
            <div class="other">
                <a href="/index.php">Home</a>
                <a href="/sobre.php">Sobre</a>
            </div>
        </body>
        </html>
        """
        links = repo._extract_article_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://repositorio.usp.br/item/002305632", links)
        self.assertIn("https://repositorio.usp.br/item/002401928", links)

    def test_extract_metadata(self) -> None:
        repo = UspRepository()
        html = """
        <html>
        <head>
            <title>ReP USP - Detalhe do registro: Comportamento dos herbicidas ametrina e glifosato</title>
            <meta name="citation_title" content="Comportamento dos herbicidas ametrina e glifosato" />
            <meta name="citation_author" content="Alves, Paulo Alexandre de Toledo" />
            <meta name="citation_author" content="Tornisielo, Valdemar Luiz" />
            <meta name="citation_abstract" content="Avaliou-se a degradacao dos herbicidas em solo canavieiro." />
            <meta name="citation_publication_date" content="2012" />
            <meta name="citation_journal_title" content="Tese (Doutorado) - Centro de Energia Nuclear na Agricultura" />
            <meta name="citation_doi" content="10.11606/D.64.2012.tde-25092012-171444" />
            <meta name="citation_pdf_url" content="http://www.teses.usp.br/teses/disponiveis/64/64135/publico/tese.pdf" />
        </head>
        <body>
            <a href='result.php?filter[]=unidadeUSP:"CENA"'>CENA</a>
        </body>
        </html>
        """
        url = "https://repositorio.usp.br/item/002305632"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "usp_002305632")
        self.assertEqual(meta["title"], "Comportamento dos herbicidas ametrina e glifosato")
        self.assertEqual(meta["authors"], ["Alves, Paulo Alexandre de Toledo", "Tornisielo, Valdemar Luiz"])
        self.assertEqual(meta["abstract"], "Avaliou-se a degradacao dos herbicidas em solo canavieiro.")
        self.assertEqual(meta["publication_date"], "2012")
        self.assertEqual(meta["journal"], "Tese (Doutorado) - Centro de Energia Nuclear na Agricultura")
        self.assertEqual(meta["doi"], "10.11606/D.64.2012.tde-25092012-171444")
        self.assertEqual(meta["pdf_url"], "http://www.teses.usp.br/teses/disponiveis/64/64135/publico/tese.pdf")
        self.assertEqual(meta["source_repository"], "usp")
        self.assertEqual(meta["faculty"], "CENA")

    def test_extract_metadata_fallback(self) -> None:
        repo = UspRepository()
        html = """
        <html>
        <head>
            <title>ReP USP - Detalhe do registro: Estudo de impacto ambiental</title>
        </head>
        <body>
            <p class="uk-text-lead">Estudo de impacto ambiental</p>
            <p class="uk-article-meta">
                <a class="link" href='result.php?filter[]=author.person.name:"Silva, Maria"'>Silva, Maria</a>
            </p>
            <div class="resumo">
                Resumo sobre impacto no ecossistema paulista.
            </div>
            <a href="https://doi.org/10.11606/artigo.2020.100">DOI</a>
            <a href="/download/artigo.pdf">PDF de acesso aberto</a>
        </body>
        </html>
        """
        url = "https://repositorio.usp.br/item/001999999"
        meta = repo._extract_metadata(html, url)
        self.assertEqual(meta["paper_id"], "usp_001999999")
        self.assertEqual(meta["title"], "Estudo de impacto ambiental")
        self.assertEqual(meta["authors"], ["Silva, Maria"])
        self.assertEqual(meta["abstract"], "Resumo sobre impacto no ecossistema paulista.")
        self.assertEqual(meta["doi"], "10.11606/artigo.2020.100")
        self.assertEqual(meta["pdf_url"], "https://repositorio.usp.br/download/artigo.pdf")

    def test_search_papers(self) -> None:
        repo = UspRepository()
        search_html = """
        <html>
        <body>
            <article class="uk-article">
                <p class="uk-text-lead title-link">
                    <a class="uk-link-reset" href="item/002305632">Herbicidas em cana</a>
                </p>
            </article>
        </body>
        </html>
        """
        item_html = """
        <html>
        <head>
            <meta name="citation_title" content="Herbicidas em cana" />
            <meta name="citation_author" content="Alves, P." />
            <meta name="citation_publication_date" content="2012" />
        </head>
        <body></body>
        </html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str = "") -> None:
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            if "result.php" in url:
                return FakeResponse(search_html, url)
            if "item/002305632" in url:
                return FakeResponse(item_html, url)
            return None

        repo.http.get = MagicMock(side_effect=fake_get)
        results = repo.search_papers("glifosato", limit=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Herbicidas em cana")
        self.assertEqual(results[0]["paper_id"], "usp_002305632")
        self.assertEqual(results[0]["authors"], ["Alves, P."])

    def test_search_papers_with_filters(self) -> None:
        repo = UspRepository()
        captured_params = {}

        class FakeResponse:
            def __init__(self, text: str = "<html><body></body></html>") -> None:
                self.text = text
                self.url = "https://repositorio.usp.br/result.php"

        def fake_get(url, params=None, timeout=30):
            nonlocal captured_params
            captured_params = params or {}
            return FakeResponse()

        repo.http.get = MagicMock(side_effect=fake_get)

        # Faculty filter
        repo.search_papers("biocombustivel", limit=5, faculty="ESALQ")
        self.assertIn("filter[]", captured_params)
        self.assertEqual(captured_params["filter[]"], 'unidadeUSP:"ESALQ"')

        # Base filter
        repo.search_papers("biocombustivel", limit=5, base="teses")
        self.assertIn("filter[]", captured_params)
        self.assertEqual(captured_params["filter[]"], 'base:"Teses e dissertações"')

    def test_get_paper_metadata(self) -> None:
        repo = UspRepository()
        item_html = """
        <html>
        <head>
            <meta name="citation_title" content="Artigo USP Teste" />
            <meta name="citation_author" content="Autor Teste" />
        </head>
        <body></body>
        </html>
        """

        class FakeResponse:
            def __init__(self, text: str, url: str) -> None:
                self.text = text
                self.url = url

        def fake_get(url, params=None, timeout=30):
            return FakeResponse(item_html, url)

        repo.http.get = MagicMock(side_effect=fake_get)

        # Using paper_id
        meta1 = repo.get_paper_metadata("usp_001234567")
        self.assertEqual(meta1["paper_id"], "usp_001234567")
        self.assertEqual(meta1["title"], "Artigo USP Teste")

        # Using full URL
        meta2 = repo.get_paper_metadata("https://repositorio.usp.br/item/001234567")
        self.assertEqual(meta2["paper_id"], "usp_001234567")
        self.assertEqual(meta2["title"], "Artigo USP Teste")

    def test_get_paper_metadata_not_found(self) -> None:
        repo = UspRepository()
        repo.http.get = MagicMock(return_value=None)

        with self.assertRaises(RepositoryError):
            repo.get_paper_metadata("usp_not_found")

    def test_download_paper(self) -> None:
        repo = UspRepository()
        item_html = """
        <html>
        <head>
            <meta name="citation_title" content="Artigo com PDF" />
            <meta name="citation_author" content="Pesquisador USP" />
            <meta name="citation_pdf_url" content="https://repositorio.usp.br/files/artigo.pdf" />
        </head>
        <body></body>
        </html>
        """

        class FakeHtmlResponse:
            text = item_html
            url = "https://repositorio.usp.br/item/009999999"

        class FakePdfResponse:
            content = b"%PDF-1.4 sample pdf bytes"
            headers = {"content-type": "application/pdf"}

        def fake_get(url, params=None, timeout=30):
            if "artigo.pdf" in url:
                return FakePdfResponse()
            return FakeHtmlResponse()

        repo.http.get = MagicMock(side_effect=fake_get)

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            res = repo.download_paper("usp_009999999", tmp_path, formats=["pdf"])
            self.assertTrue(res["success"])
            self.assertEqual(res["paper_id"], "usp_009999999")

            meta_file = tmp_path / "usp_009999999_metadata.json"
            pdf_file = tmp_path / "usp_009999999.pdf"
            self.assertTrue(meta_file.exists())
            self.assertTrue(pdf_file.exists())

            saved_json = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertEqual(saved_json["title"], "Artigo com PDF")
            self.assertEqual(saved_json["source_repository"], "usp")

    def test_get_repository_info(self) -> None:
        repo = UspRepository()
        info = repo.get_repository_info()
        self.assertEqual(info["name"], "USP")
        self.assertIn("repositorio.usp.br", info["base_url"])
        self.assertIn("pdf", info["supported_formats"])
        self.assertIn("metadata", info["supported_formats"])


if __name__ == "__main__":
    unittest.main()
