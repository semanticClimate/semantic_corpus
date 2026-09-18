"""Convert PDF documents to HTML (and XML) using Docling.

Provides single-file and corpus-wide batch conversion so that HTML and XML
representations are available regardless of the source format of the paper.
"""

import html
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.transformation.xml_to_html import convert_xml_to_html

logger = logging.getLogger(__name__)

_CONVERTER_CACHE: Dict[bool, Any] = {}


def get_docling_converter(*, do_ocr: bool = False) -> Any:
    """Get or create a cached Docling DocumentConverter instance.

    Args:
        do_ocr: If True, enable OCR for scanned PDFs. If False (default),
            disable OCR for fast parsing of programmatic PDFs.

    Returns:
        DocumentConverter instance.

    Raises:
        CorpusError: If docling is not installed or initialization fails.
    """
    if do_ocr in _CONVERTER_CACHE:
        return _CONVERTER_CACHE[do_ocr]

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise CorpusError(
            f"Docling is required for PDF conversion but is not installed: {exc}. "
            "Please install docling (e.g. pip install docling)."
        ) from exc

    try:
        pipeline_options = PdfPipelineOptions(do_ocr=do_ocr)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        _CONVERTER_CACHE[do_ocr] = converter
        return converter
    except Exception as exc:
        raise CorpusError(f"Failed to initialize Docling DocumentConverter: {exc}") from exc


def convert_pdf_to_html(
    pdf_path: Union[Path, str],
    html_path: Union[Path, str],
    *,
    xml_path: Optional[Union[Path, str]] = None,
    generate_xml: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    do_ocr: bool = False,
    page_range: Optional[Tuple[int, int]] = None,
    docling_converter: Optional[Any] = None,
) -> Path:
    """Convert a PDF document to HTML (and optionally XML) using Docling.

    Args:
        pdf_path: Path to the input PDF file.
        html_path: Destination path for the generated HTML file.
        xml_path: Optional destination path for DocTags XML file.
        generate_xml: If True and xml_path is None, generate XML alongside HTML.
        metadata: Optional metadata dictionary (e.g. title) to inject into HTML.
        do_ocr: If True, enable OCR during conversion.
        page_range: Optional tuple of (start_page, end_page) 1-indexed.
        docling_converter: Optional pre-initialized DocumentConverter instance.

    Returns:
        Path to the generated HTML file.

    Raises:
        CorpusError: If the PDF does not exist or conversion fails.
    """
    pdf_path = Path(pdf_path)
    html_path = Path(html_path)

    if not pdf_path.is_file():
        raise CorpusError(f"PDF file not found: {pdf_path}")

    converter = docling_converter or get_docling_converter(do_ocr=do_ocr)

    convert_kwargs: Dict[str, Any] = {}
    if page_range is not None:
        convert_kwargs["page_range"] = page_range

    try:
        conv_res = converter.convert(str(pdf_path), **convert_kwargs)
        document = conv_res.document
        html_content = document.export_to_html()
    except Exception as exc:
        raise CorpusError(f"Failed to convert PDF to HTML '{pdf_path}': {exc}") from exc

    # Inject title into HTML if metadata specifies it
    title = (metadata or {}).get("title")
    if title:
        escaped_title = html.escape(title)
        if "<title>" in html_content:
            html_content = re.sub(
                r"<title>.*?</title>",
                f"<title>{escaped_title}</title>",
                html_content,
                count=1,
                flags=re.DOTALL,
            )
        elif "<head>" in html_content:
            html_content = html_content.replace(
                "<head>",
                f"<head>\n<title>{escaped_title}</title>",
                1,
            )

    try:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_content, encoding="utf-8")
    except OSError as exc:
        raise CorpusError(f"Cannot write HTML file '{html_path}': {exc}") from exc

    # Optionally generate XML (DocTags format)
    target_xml = xml_path or (html_path.with_suffix(".xml") if generate_xml else None)
    if target_xml:
        target_xml = Path(target_xml)
        try:
            doctags = document.export_to_doctags()
            if not doctags.strip().startswith("<?xml"):
                xml_content = f'<?xml version="1.0" encoding="utf-8"?>\n{doctags}'
            else:
                xml_content = doctags
            target_xml.parent.mkdir(parents=True, exist_ok=True)
            target_xml.write_text(xml_content, encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to generate DocTags XML for %s: %s", pdf_path, exc)

    return html_path


def convert_pdf_to_xml(
    pdf_path: Union[Path, str],
    xml_path: Union[Path, str],
    *,
    do_ocr: bool = False,
    page_range: Optional[Tuple[int, int]] = None,
    docling_converter: Optional[Any] = None,
) -> Path:
    """Convert a PDF document to DocTags XML using Docling.

    Args:
        pdf_path: Path to the input PDF file.
        xml_path: Destination path for the generated XML file.
        do_ocr: If True, enable OCR during conversion.
        page_range: Optional tuple of (start_page, end_page) 1-indexed.
        docling_converter: Optional pre-initialized DocumentConverter instance.

    Returns:
        Path to the generated XML file.

    Raises:
        CorpusError: If the PDF does not exist or conversion fails.
    """
    pdf_path = Path(pdf_path)
    xml_path = Path(xml_path)

    if not pdf_path.is_file():
        raise CorpusError(f"PDF file not found: {pdf_path}")

    converter = docling_converter or get_docling_converter(do_ocr=do_ocr)

    convert_kwargs: Dict[str, Any] = {}
    if page_range is not None:
        convert_kwargs["page_range"] = page_range

    try:
        conv_res = converter.convert(str(pdf_path), **convert_kwargs)
        document = conv_res.document
        doctags = document.export_to_doctags()
    except Exception as exc:
        raise CorpusError(f"Failed to convert PDF to XML '{pdf_path}': {exc}") from exc

    if not doctags.strip().startswith("<?xml"):
        xml_content = f'<?xml version="1.0" encoding="utf-8"?>\n{doctags}'
    else:
        xml_content = doctags

    try:
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        xml_path.write_text(xml_content, encoding="utf-8")
    except OSError as exc:
        raise CorpusError(f"Cannot write XML file '{xml_path}': {exc}") from exc

    return xml_path


def convert_corpus_pdf_to_html(
    corpus_dir: Union[Path, str],
    *,
    overwrite: bool = False,
    generate_xml: bool = True,
    do_ocr: bool = False,
    continue_on_error: bool = True,
) -> Dict[str, Path]:
    """Convert all PDF files in a BAGIT corpus to HTML (and XML) under data/documents/.

    Args:
        corpus_dir: Path to the corpus root directory.
        overwrite: If True, re-convert existing HTML/XML files.
        generate_xml: If True, also generate XML (doctags) for PDFs lacking XML.
        do_ocr: If True, enable OCR for PDFs.
        continue_on_error: If True, log errors and continue converting other papers.

    Returns:
        Dictionary mapping paper_id -> generated HTML Path.

    Raises:
        CorpusError: If corpus PDF directory is missing or unrecoverable error occurs.
    """
    corpus_dir = Path(corpus_dir)
    pdf_dir = corpus_dir / "data" / "documents" / "pdf"
    html_dir = corpus_dir / "data" / "documents" / "html"
    xml_dir = corpus_dir / "data" / "documents" / "xml"

    if not pdf_dir.is_dir():
        raise CorpusError(f"Corpus PDF directory not found: {pdf_dir}")

    html_dir.mkdir(parents=True, exist_ok=True)
    if generate_xml:
        xml_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return {}

    converter = get_docling_converter(do_ocr=do_ocr)
    written: Dict[str, Path] = {}

    for pdf_path in pdf_files:
        paper_id = pdf_path.stem
        html_path = html_dir / f"{paper_id}.html"
        xml_path = xml_dir / f"{paper_id}.xml"

        needs_html = overwrite or not html_path.exists()
        needs_xml = generate_xml and (overwrite or not xml_path.exists())

        if not needs_html and not needs_xml:
            written[paper_id] = html_path
            continue

        try:
            convert_pdf_to_html(
                pdf_path,
                html_path,
                xml_path=xml_path if needs_xml else None,
                generate_xml=needs_xml,
                do_ocr=do_ocr,
                docling_converter=converter,
            )
            written[paper_id] = html_path
        except CorpusError as exc:
            if continue_on_error:
                logger.error("Skipping PDF conversion for %s: %s", paper_id, exc)
            else:
                raise

    # Update BAGIT manifest if BAGIT bag exists
    try:
        from semantic_corpus.storage.bagit_manager import BagitManager
        bm = BagitManager(corpus_dir)
        if bm.validate_bag():
            bm.update_manifest()
    except Exception as exc:
        logger.debug("BAGIT manifest update skipped or failed: %s", exc)

    return written


def ensure_corpus_formats(
    corpus_dir: Union[Path, str],
    *,
    overwrite: bool = False,
    do_ocr: bool = False,
    generate_xml_from_pdf: bool = True,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    """Ensure both HTML and XML formats are available for all papers regardless of origin.

    For papers with XML source (e.g. Europe PMC JATS XML):
        - If HTML is missing (or overwrite=True), converts XML -> HTML.
    For papers with PDF source (e.g. arXiv, SciELO, UNAM, CONICET, etc.):
        - If HTML is missing (or overwrite=True), converts PDF -> HTML using Docling.
        - If XML is missing (or overwrite=True) and generate_xml_from_pdf=True,
          generates DocTags XML from PDF using Docling.

    Args:
        corpus_dir: Path to the corpus root directory.
        overwrite: If True, re-convert existing HTML/XML files.
        do_ocr: If True, enable OCR for PDF conversion.
        generate_xml_from_pdf: If True, generate XML for PDF papers that lack XML.
        continue_on_error: If True, log errors and continue processing remaining papers.

    Returns:
        Dictionary with conversion results and availability report.
    """
    corpus_dir = Path(corpus_dir)
    docs_dir = corpus_dir / "data" / "documents"
    xml_dir = docs_dir / "xml"
    pdf_dir = docs_dir / "pdf"
    html_dir = docs_dir / "html"

    html_dir.mkdir(parents=True, exist_ok=True)
    xml_dir.mkdir(parents=True, exist_ok=True)

    result_summary: Dict[str, Any] = {
        "converted_xml_to_html": [],
        "converted_pdf_to_html": [],
        "converted_pdf_to_xml": [],
        "errors": [],
        "papers": {},
    }

    # Step 1: Process papers with XML source
    if xml_dir.is_dir():
        for xml_path in sorted(xml_dir.glob("*.xml")):
            paper_id = xml_path.stem
            html_path = html_dir / f"{paper_id}.html"

            if overwrite or not html_path.exists():
                try:
                    convert_xml_to_html(xml_path, html_path)
                    result_summary["converted_xml_to_html"].append(paper_id)
                except Exception as exc:
                    err_msg = f"XML to HTML failed for {paper_id}: {exc}"
                    result_summary["errors"].append(err_msg)
                    if not continue_on_error:
                        raise CorpusError(err_msg) from exc
                    logger.error(err_msg)

    # Step 2: Process papers with PDF source
    if pdf_dir.is_dir():
        pdf_files = sorted(pdf_dir.glob("*.pdf"))
        if pdf_files:
            converter = None
            for pdf_path in pdf_files:
                paper_id = pdf_path.stem
                html_path = html_dir / f"{paper_id}.html"
                xml_path = xml_dir / f"{paper_id}.xml"

                needs_html = overwrite or not html_path.exists()
                needs_xml = generate_xml_from_pdf and (overwrite or not xml_path.exists())

                if not needs_html and not needs_xml:
                    continue

                if converter is None:
                    converter = get_docling_converter(do_ocr=do_ocr)

                try:
                    convert_pdf_to_html(
                        pdf_path,
                        html_path,
                        xml_path=xml_path if needs_xml else None,
                        generate_xml=needs_xml,
                        do_ocr=do_ocr,
                        docling_converter=converter,
                    )
                    if needs_html:
                        result_summary["converted_pdf_to_html"].append(paper_id)
                    if needs_xml and xml_path.exists():
                        result_summary["converted_pdf_to_xml"].append(paper_id)
                except Exception as exc:
                    err_msg = f"PDF conversion failed for {paper_id}: {exc}"
                    result_summary["errors"].append(err_msg)
                    if not continue_on_error:
                        raise CorpusError(err_msg) from exc
                    logger.error(err_msg)

    # Step 3: Populate availability map for all papers
    all_paper_ids = set()
    for sub in (pdf_dir, xml_dir, html_dir):
        if sub.is_dir():
            for f in sub.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    all_paper_ids.add(f.stem)

    for paper_id in sorted(all_paper_ids):
        p_html = html_dir / f"{paper_id}.html"
        p_xml = xml_dir / f"{paper_id}.xml"
        p_pdf = pdf_dir / f"{paper_id}.pdf"
        result_summary["papers"][paper_id] = {
            "html": p_html if p_html.exists() else None,
            "xml": p_xml if p_xml.exists() else None,
            "pdf": p_pdf if p_pdf.exists() else None,
            "has_both_html_and_xml": p_html.exists() and p_xml.exists(),
        }

    # Step 4: Update BAGIT manifest if BAGIT bag exists
    try:
        from semantic_corpus.storage.bagit_manager import BagitManager
        bm = BagitManager(corpus_dir)
        if bm.validate_bag():
            bm.update_manifest()
    except Exception as exc:
        logger.debug("BAGIT manifest update skipped or failed: %s", exc)

    return result_summary
