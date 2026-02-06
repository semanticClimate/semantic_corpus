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
        assert processor is not None, "MetadataProcessor should be initialized"

    def test_process_xml_metadata(self, sample_xml_path: Path):
        """Test processing XML metadata."""
        processor = MetadataProcessor()
        
        metadata = processor.process_xml_metadata(sample_xml_path)
        
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        assert "title" in metadata, "Metadata should contain 'title' field"
        assert "abstract" in metadata, "Metadata should contain 'abstract' field"
        assert "doi" in metadata, "Metadata should contain 'doi' field"
        assert metadata["title"] == "Sample Article", f"Expected title 'Sample Article', got '{metadata.get('title')}'"
        assert metadata["abstract"] == "This is a sample abstract for testing.", f"Expected abstract 'This is a sample abstract for testing.', got '{metadata.get('abstract')}'"

    def test_process_pdf_metadata(self, sample_pdf_path: Path):
        """Test processing PDF metadata."""
        processor = MetadataProcessor()
        
        metadata = processor.process_pdf_metadata(sample_pdf_path)
        
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        # PDF metadata might be limited, but should have basic structure
        assert "file_path" in metadata, "Metadata should contain 'file_path' field"
        assert "file_type" in metadata, "Metadata should contain 'file_type' field"
        assert metadata["file_type"] == "pdf", f"Expected file_type 'pdf', got '{metadata.get('file_type')}'"

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
        
        assert normalized["title"] == "Sample Title", f"Expected normalized title 'Sample Title', got '{normalized.get('title')}'"
        assert normalized["abstract"] == "Sample abstract text", f"Expected normalized abstract 'Sample abstract text', got '{normalized.get('abstract')}'"
        assert normalized["doi"] == "10.1000/sample", f"Expected normalized doi '10.1000/sample', got '{normalized.get('doi')}'"
        assert normalized["authors"] == ["Author 1", "Author 2"], f"Expected normalized authors ['Author 1', 'Author 2'], got '{normalized.get('authors')}'"
        assert normalized["publication_date"] == "2024-01-01", f"Expected normalized publication_date '2024-01-01', got '{normalized.get('publication_date')}'"

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
        
        assert processor.validate_metadata(valid_metadata) is True, "Valid metadata should return True"
        
        # Test invalid metadata (missing required fields)
        invalid_metadata = {
            "title": "Sample Title",
            # Missing abstract, doi, etc.
        }
        
        assert processor.validate_metadata(invalid_metadata) is False, "Invalid metadata (missing required fields) should return False"

    def test_extract_keywords(self):
        """Test extracting keywords from text."""
        processor = MetadataProcessor()
        
        text = "This paper discusses climate change adaptation strategies and mitigation approaches."
        
        keywords = processor.extract_keywords(text)
        
        assert isinstance(keywords, list), "Keywords should be a list"
        assert len(keywords) > 0, "Keywords list should not be empty"
        # Should contain relevant terms
        assert any("climate" in keyword.lower() for keyword in keywords), "Keywords should contain 'climate'"
        assert any("adaptation" in keyword.lower() for keyword in keywords), "Keywords should contain 'adaptation'"


class TestMetadataExtractor:
    """Test cases for MetadataExtractor class."""

    def test_metadata_extractor_initialization(self):
        """Test that MetadataExtractor can be initialized."""
        extractor = MetadataExtractor()
        assert extractor is not None, "MetadataExtractor should be initialized"

    def test_extract_from_xml(self, sample_xml_path: Path):
        """Test extracting metadata from XML file."""
        extractor = MetadataExtractor()
        
        metadata = extractor.extract_from_xml(sample_xml_path)
        
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        assert "title" in metadata, "Metadata should contain 'title' field"
        assert "abstract" in metadata, "Metadata should contain 'abstract' field"
        assert "doi" in metadata, "Metadata should contain 'doi' field"

    def test_extract_from_pdf(self, sample_pdf_path: Path):
        """Test extracting metadata from PDF file."""
        extractor = MetadataExtractor()
        
        metadata = extractor.extract_from_pdf(sample_pdf_path)
        
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        assert "file_path" in metadata, "Metadata should contain 'file_path' field"
        assert "file_type" in metadata, "Metadata should contain 'file_type' field"

    def test_extract_from_json(self):
        """Test extracting metadata from JSON file."""
        extractor = MetadataExtractor()
        
        # Use static test resource file
        json_path = Path(Path(__file__).parent, "resources", "sample.json")
        
        metadata = extractor.extract_from_json(json_path)
        
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        assert metadata["title"] == "Sample Article", f"Expected title 'Sample Article', got '{metadata.get('title')}'"
        assert metadata["abstract"] == "Sample abstract", f"Expected abstract 'Sample abstract', got '{metadata.get('abstract')}'"
        assert metadata["doi"] == "10.1000/sample", f"Expected doi '10.1000/sample', got '{metadata.get('doi')}'"
        assert metadata["authors"] == ["Author 1", "Author 2"], f"Expected authors ['Author 1', 'Author 2'], got '{metadata.get('authors')}'"

    def test_extract_raises_error_for_unsupported_format(self):
        """Test that extractor raises error for unsupported file formats."""
        extractor = MetadataExtractor()
        
        # Use static test resource file
        unsupported_path = Path(Path(__file__).parent, "resources", "sample.txt")
        
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
        assert validator.validate_doi("10.1000/sample") is True, "Valid DOI '10.1000/sample' should return True"
        assert validator.validate_doi("10.1038/nature12345") is True, "Valid DOI '10.1038/nature12345' should return True"
        
        # Test invalid DOIs
        assert validator.validate_doi("invalid-doi") is False, "Invalid DOI 'invalid-doi' should return False"
        assert validator.validate_doi("") is False, "Empty DOI should return False"
        assert validator.validate_doi(None) is False, "None DOI should return False"

    def test_validate_publication_date(self):
        """Test validating publication date format."""
        from semantic_corpus.tools.metadata_validator import MetadataValidator
        
        validator = MetadataValidator()
        
        # Test valid dates
        assert validator.validate_publication_date("2024-01-01") is True, "Valid date '2024-01-01' should return True"
        assert validator.validate_publication_date("2023-12-31") is True, "Valid date '2023-12-31' should return True"
        
        # Test invalid dates
        assert validator.validate_publication_date("invalid-date") is False, "Invalid date 'invalid-date' should return False"
        assert validator.validate_publication_date("2024-13-01") is False, "Invalid date '2024-13-01' (invalid month) should return False"
        assert validator.validate_publication_date("") is False, "Empty date should return False"

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
        
        assert validator.validate_required_fields(complete_metadata) is True, "Complete metadata should return True"
        
        # Test incomplete metadata
        incomplete_metadata = {
            "title": "Sample Title",
            # Missing other required fields
        }
        
        assert validator.validate_required_fields(incomplete_metadata) is False, "Incomplete metadata (missing required fields) should return False"
