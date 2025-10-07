"""Metadata validation functionality."""

import re
from datetime import datetime
from typing import Dict, Any, List


class MetadataValidator:
    """Validates metadata fields and formats."""

    def __init__(self) -> None:
        """Initialize metadata validator."""
        pass

    def validate_doi(self, doi: str) -> bool:
        """Validate DOI format.
        
        Args:
            doi: DOI string to validate
            
        Returns:
            True if DOI is valid, False otherwise
        """
        if not doi or not isinstance(doi, str):
            return False
        
        # Basic DOI pattern validation
        doi_pattern = r'^10\.\d{4,}/[^\s]+$'
        return bool(re.match(doi_pattern, doi.strip()))

    def validate_publication_date(self, date_str: str) -> bool:
        """Validate publication date format.
        
        Args:
            date_str: Date string to validate (YYYY-MM-DD format)
            
        Returns:
            True if date is valid, False otherwise
        """
        if not date_str or not isinstance(date_str, str):
            return False
        
        try:
            # Try to parse the date
            datetime.strptime(date_str.strip(), '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def validate_required_fields(self, metadata: Dict[str, Any]) -> bool:
        """Validate that all required fields are present and non-empty.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            True if all required fields are present, False otherwise
        """
        required_fields = ['title', 'abstract', 'doi', 'authors', 'publication_date']
        
        for field in required_fields:
            if field not in metadata:
                return False
            
            value = metadata[field]
            if not value or (isinstance(value, str) and not value.strip()):
                return False
            
            if isinstance(value, list) and len(value) == 0:
                return False
        
        return True

    def validate_authors(self, authors: List[str]) -> bool:
        """Validate authors list.
        
        Args:
            authors: List of author names
            
        Returns:
            True if authors list is valid, False otherwise
        """
        if not isinstance(authors, list) or len(authors) == 0:
            return False
        
        for author in authors:
            if not isinstance(author, str) or not author.strip():
                return False
        
        return True

    def validate_title(self, title: str) -> bool:
        """Validate title.
        
        Args:
            title: Title string to validate
            
        Returns:
            True if title is valid, False otherwise
        """
        if not isinstance(title, str) or not title.strip():
            return False
        
        # Title should be at least 10 characters and not too long
        return 10 <= len(title.strip()) <= 500

    def validate_abstract(self, abstract: str) -> bool:
        """Validate abstract.
        
        Args:
            abstract: Abstract string to validate
            
        Returns:
            True if abstract is valid, False otherwise
        """
        if not isinstance(abstract, str) or not abstract.strip():
            return False
        
        # Abstract should be at least 50 characters
        return len(abstract.strip()) >= 50

    def validate_metadata_completeness(self, metadata: Dict[str, Any]) -> Dict[str, bool]:
        """Validate metadata completeness and return detailed results.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Dictionary with validation results for each field
        """
        results = {}
        
        # Check required fields
        required_fields = ['title', 'abstract', 'doi', 'authors', 'publication_date']
        for field in required_fields:
            results[f'{field}_present'] = field in metadata and bool(metadata.get(field))
        
        # Validate specific field formats
        if 'doi' in metadata:
            results['doi_valid'] = self.validate_doi(metadata['doi'])
        
        if 'publication_date' in metadata:
            results['publication_date_valid'] = self.validate_publication_date(metadata['publication_date'])
        
        if 'authors' in metadata:
            results['authors_valid'] = self.validate_authors(metadata['authors'])
        
        if 'title' in metadata:
            results['title_valid'] = self.validate_title(metadata['title'])
        
        if 'abstract' in metadata:
            results['abstract_valid'] = self.validate_abstract(metadata['abstract'])
        
        return results
