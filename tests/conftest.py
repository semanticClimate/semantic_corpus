"""Pytest configuration and fixtures for semantic_corpus tests."""

import pytest
import tempfile
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing in project corpora folder."""
    # Use project corpora directory for all test files and directories
    project_corpora = Path(Path(__file__).parent.parent, "corpora")
    project_corpora.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryDirectory(dir=project_corpora) as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_pdf_path() -> Path:
    """Return path to sample PDF file for testing."""
    return Path(Path(__file__).parent, "resources", "sample.pdf")


@pytest.fixture
def sample_xml_path() -> Path:
    """Return path to sample XML file for testing."""
    return Path(Path(__file__).parent, "resources", "sample.xml")


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
