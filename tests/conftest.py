"""Pytest configuration and fixtures for semantic_corpus tests."""

import pytest
import tempfile
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing in project corpora folder."""
    # Use project corpora directory for all test files and directories
    project_corpora = Path(__file__).parent.parent / "corpora"
    project_corpora.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryDirectory(dir=project_corpora) as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_pdf_path(temp_dir: Path) -> Path:
    """Create a sample PDF file for testing."""
    pdf_path = temp_dir / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Sample PDF content")
    return pdf_path


@pytest.fixture
def sample_xml_path(temp_dir: Path) -> Path:
    """Create a sample XML file for testing."""
    xml_path = temp_dir / "sample.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<article>
    <title>Sample Article</title>
    <abstract>This is a sample abstract for testing.</abstract>
    <doi>10.1000/sample</doi>
</article>"""
    xml_path.write_text(xml_content)
    return xml_path


@pytest.fixture
def sample_metadata() -> dict:
    """Sample metadata for testing."""
    return {
        "title": "Sample Article",
        "abstract": "This is a sample abstract for testing.",
        "doi": "10.1000/sample",
        "authors": ["John Doe", "Jane Smith"],
        "publication_date": "2024-01-01",
        "journal": "Test Journal",
        "pmcid": "PMC123456",
        "pmid": "12345678",
    }
