"""Metadata extraction functionality."""

import json
from pathlib import Path
from typing import Dict, Any

from semantic_corpus.core.exceptions import MetadataError


class MetadataExtractor:
    """Extracts metadata from various file formats."""

    def __init__(self) -> None:
        """Initialize metadata extractor."""
        pass

    def extract_from_xml(self, xml_path: Path) -> Dict[str, Any]:
        """Extract metadata from XML file.
        
        Args:
            xml_path: Path to XML file
            
        Returns:
            Extracted metadata dictionary
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
            raise MetadataError(f"Failed to extract metadata from XML: {e}")

    def extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted metadata dictionary
        """
        try:
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
            except Exception:
                # PyPDF2 is available but the PDF may be malformed/partial.
                # Fall back to basic file metadata rather than failing.
                pass
            
            return metadata
            
        except Exception as e:
            raise MetadataError(f"Failed to extract metadata from PDF: {e}")

    def extract_from_json(self, json_path: Path) -> Dict[str, Any]:
        """Extract metadata from JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Extracted metadata dictionary
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata
            
        except Exception as e:
            raise MetadataError(f"Failed to extract metadata from JSON: {e}")

    def extract_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file based on extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted metadata dictionary
            
        Raises:
            MetadataError: If file format is not supported
        """
        if not file_path.exists():
            raise MetadataError(f"File not found: {file_path}")
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.xml':
            return self.extract_from_xml(file_path)
        elif suffix == '.pdf':
            return self.extract_from_pdf(file_path)
        elif suffix == '.json':
            return self.extract_from_json(file_path)
        else:
            raise MetadataError(f"Unsupported file format: {suffix}")
