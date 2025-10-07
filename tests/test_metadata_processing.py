"""Tests for metadata processing functionality."""

import pytest
from pathlib import Path
from semantic_corpus.tools.metadata_processor import MetadataProcessor
from semantic_corpus.tools.metadata_extractor import MetadataExtractor
from semantic_corpus.core.exceptions import MetadataError


class TestMetadataProcessor:
    """Test cases for MetadataProcessor class."""

    def test_metadata_processor_initialization(self):
        """Test that MetadataProcessor can be initialized."""
        processor = MetadataProcessor()
        assert processor is not None

    def test_process_xml_metadata(self, sample_xml_path: Path):
        """Test processing XML metadata."""
        processor = MetadataProcessor()
        
        metadata = processor.process_xml_metadata(sample_xml_path)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "abstract" in metadata
        assert "doi" in metadata
        assert metadata["title"] == "Sample Article"
        assert metadata["abstract"] == "This is a sample abstract for testing."

    def test_process_pdf_metadata(self, sample_pdf_path: Path):
        """Test processing PDF metadata."""
        processor = MetadataProcessor()
        
        metadata = processor.process_pdf_metadata(sample_pdf_path)
        
        assert isinstance(metadata, dict)
        # PDF metadata might be limited, but should have basic structure
        assert "file_path" in metadata
        assert "file_type" in metadata
        assert metadata["file_type"] == "pdf"

    def test_normalize_metadata(self):
        """Test normalizing metadata from different sources."""
        processor = MetadataProcessor()
        
        # Test with different metadata formats
        raw_metadata = {
            "Title": "Sample Title",
            "Abstract": "Sample abstract text",
            "DOI": "10.1000/sample",
            "Authors": ["Author 1", "Author 2"],
            "Publication_Date": "2024-01-01"
        }
        
        normalized = processor.normalize_metadata(raw_metadata)
        
        assert normalized["title"] == "Sample Title"
        assert normalized["abstract"] == "Sample abstract text"
        assert normalized["doi"] == "10.1000/sample"
        assert normalized["authors"] == ["Author 1", "Author 2"]
        assert normalized["publication_date"] == "2024-01-01"

    def test_validate_metadata(self):
        """Test validating metadata."""
        processor = MetadataProcessor()
        
        # Test valid metadata
        valid_metadata = {
            "title": "Sample Title",
            "abstract": "Sample abstract",
            "doi": "10.1000/sample",
            "authors": ["Author 1"],
            "publication_date": "2024-01-01"
        }
        
        assert processor.validate_metadata(valid_metadata) is True
        
        # Test invalid metadata (missing required fields)
        invalid_metadata = {
            "title": "Sample Title",
            # Missing abstract, doi, etc.
        }
        
        assert processor.validate_metadata(invalid_metadata) is False

    def test_extract_keywords(self):
        """Test extracting keywords from text."""
        processor = MetadataProcessor()
        
        text = "This paper discusses climate change adaptation strategies and mitigation approaches."
        
        keywords = processor.extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should contain relevant terms
        assert any("climate" in keyword.lower() for keyword in keywords)
        assert any("adaptation" in keyword.lower() for keyword in keywords)


class TestMetadataExtractor:
    """Test cases for MetadataExtractor class."""

    def test_metadata_extractor_initialization(self):
        """Test that MetadataExtractor can be initialized."""
        extractor = MetadataExtractor()
        assert extractor is not None

    def test_extract_from_xml(self, sample_xml_path: Path):
        """Test extracting metadata from XML file."""
        extractor = MetadataExtractor()
        
        metadata = extractor.extract_from_xml(sample_xml_path)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "abstract" in metadata
        assert "doi" in metadata

    def test_extract_from_pdf(self, sample_pdf_path: Path):
        """Test extracting metadata from PDF file."""
        extractor = MetadataExtractor()
        
        metadata = extractor.extract_from_pdf(sample_pdf_path)
        
        assert isinstance(metadata, dict)
        assert "file_path" in metadata
        assert "file_type" in metadata

    def test_extract_from_json(self, temp_dir: Path):
        """Test extracting metadata from JSON file."""
        extractor = MetadataExtractor()
        
        # Create a sample JSON file
        json_path = temp_dir / "sample.json"
        json_content = """{
            "title": "Sample Article",
            "abstract": "Sample abstract",
            "doi": "10.1000/sample",
            "authors": ["Author 1", "Author 2"]
        }"""
        json_path.write_text(json_content)
        
        metadata = extractor.extract_from_json(json_path)
        
        assert isinstance(metadata, dict)
        assert metadata["title"] == "Sample Article"
        assert metadata["abstract"] == "Sample abstract"
        assert metadata["doi"] == "10.1000/sample"
        assert metadata["authors"] == ["Author 1", "Author 2"]

    def test_extract_raises_error_for_unsupported_format(self, temp_dir: Path):
        """Test that extractor raises error for unsupported file formats."""
        extractor = MetadataExtractor()
        
        # Create a file with unsupported extension
        unsupported_path = temp_dir / "sample.txt"
        unsupported_path.write_text("Some text content")
        
        with pytest.raises(MetadataError):
            extractor.extract_from_file(unsupported_path)

    def test_extract_handles_missing_file(self):
        """Test that extractor handles missing files gracefully."""
        extractor = MetadataExtractor()
        
        with pytest.raises(MetadataError):
            extractor.extract_from_file(Path("nonexistent_file.xml"))


class TestMetadataValidation:
    """Test cases for metadata validation functionality."""

    def test_validate_doi_format(self):
        """Test validating DOI format."""
        from semantic_corpus.tools.metadata_validator import MetadataValidator
        
        validator = MetadataValidator()
        
        # Test valid DOIs
        assert validator.validate_doi("10.1000/sample") is True
        assert validator.validate_doi("10.1038/nature12345") is True
        
        # Test invalid DOIs
        assert validator.validate_doi("invalid-doi") is False
        assert validator.validate_doi("") is False
        assert validator.validate_doi(None) is False

    def test_validate_publication_date(self):
        """Test validating publication date format."""
        from semantic_corpus.tools.metadata_validator import MetadataValidator
        
        validator = MetadataValidator()
        
        # Test valid dates
        assert validator.validate_publication_date("2024-01-01") is True
        assert validator.validate_publication_date("2023-12-31") is True
        
        # Test invalid dates
        assert validator.validate_publication_date("invalid-date") is False
        assert validator.validate_publication_date("2024-13-01") is False  # Invalid month
        assert validator.validate_publication_date("") is False

    def test_validate_required_fields(self):
        """Test validating required metadata fields."""
        from semantic_corpus.tools.metadata_validator import MetadataValidator
        
        validator = MetadataValidator()
        
        # Test complete metadata
        complete_metadata = {
            "title": "Sample Title",
            "abstract": "Sample abstract",
            "doi": "10.1000/sample",
            "authors": ["Author 1"],
            "publication_date": "2024-01-01"
        }
        
        assert validator.validate_required_fields(complete_metadata) is True
        
        # Test incomplete metadata
        incomplete_metadata = {
            "title": "Sample Title",
            # Missing other required fields
        }
        
        assert validator.validate_required_fields(incomplete_metadata) is False
