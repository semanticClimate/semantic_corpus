"""Metadata processing functionality."""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_corpus.core.exceptions import MetadataError


class MetadataProcessor:
    """Processes and normalizes metadata from different sources."""

    def __init__(self) -> None:
        """Initialize metadata processor."""
        pass

    def process_xml_metadata(self, xml_path: Path) -> Dict[str, Any]:
        """Process metadata from XML file.
        
        Args:
            xml_path: Path to XML file
            
        Returns:
            Processed metadata dictionary
        """
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            metadata = {}
            
            # Extract title
            title_elem = root.find('.//title')
            if title_elem is not None:
                metadata['title'] = title_elem.text or ""
            
            # Extract abstract
            abstract_elem = root.find('.//abstract')
            if abstract_elem is not None:
                metadata['abstract'] = abstract_elem.text or ""
            
            # Extract DOI
            doi_elem = root.find('.//doi')
            if doi_elem is not None:
                metadata['doi'] = doi_elem.text or ""
            
            # Extract authors
            authors = []
            for author in root.findall('.//author'):
                name = author.text
                if name:
                    authors.append(name)
            metadata['authors'] = authors
            
            return metadata
            
        except Exception as e:
            raise MetadataError(f"Failed to process XML metadata: {e}")

    def process_pdf_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Process metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Processed metadata dictionary
        """
        try:
            # Basic PDF metadata extraction
            metadata = {
                'file_path': str(pdf_path),
                'file_type': 'pdf',
                'file_size': pdf_path.stat().st_size,
            }
            
            # Try to extract basic metadata using PyPDF2 if available
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    if pdf_reader.metadata:
                        pdf_metadata = pdf_reader.metadata
                        if pdf_metadata.title:
                            metadata['title'] = pdf_metadata.title
                        if pdf_metadata.author:
                            metadata['authors'] = [pdf_metadata.author]
                        if pdf_metadata.creator:
                            metadata['creator'] = pdf_metadata.creator
            except ImportError:
                # PyPDF2 not available, use basic metadata
                pass
            
            return metadata
            
        except Exception as e:
            raise MetadataError(f"Failed to process PDF metadata: {e}")

    def normalize_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata from different sources.
        
        Args:
            raw_metadata: Raw metadata dictionary
            
        Returns:
            Normalized metadata dictionary
        """
        normalized = {}
        
        # Map common field variations to standard names
        field_mapping = {
            'Title': 'title',
            'title': 'title',
            'Abstract': 'abstract',
            'abstract': 'abstract',
            'AbstractText': 'abstract',
            'DOI': 'doi',
            'doi': 'doi',
            'Authors': 'authors',
            'authors': 'authors',
            'AuthorList': 'authors',
            'Publication_Date': 'publication_date',
            'publication_date': 'publication_date',
            'firstPublicationDate': 'publication_date',
            'Journal': 'journal',
            'journal': 'journal',
            'journalTitle': 'journal',
        }
        
        for key, value in raw_metadata.items():
            normalized_key = field_mapping.get(key, key.lower())
            normalized[normalized_key] = value
        
        return normalized

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata completeness.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            True if metadata is valid, False otherwise
        """
        required_fields = ['title', 'abstract', 'doi', 'authors', 'publication_date']
        
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                return False
        
        return True

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using simple frequency analysis.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Simple keyword extraction using word frequency
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'shall', 'a', 'an', 'some', 'any', 'all', 'both',
            'each', 'every', 'no', 'not', 'only', 'also', 'just', 'even',
            'still', 'yet', 'already', 'here', 'there', 'where', 'when', 'why',
            'how', 'what', 'which', 'who', 'whom', 'whose'
        }
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]
