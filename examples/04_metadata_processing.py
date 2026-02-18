#!/usr/bin/env python3
"""
Example 4: Metadata processing - extract and normalize metadata.

This example demonstrates how to process metadata from different file formats.
"""

from pathlib import Path
from semantic_corpus.tools.metadata_processor import MetadataProcessor

processor = MetadataProcessor()

# Example: Process PDF metadata (if file exists)
pdf_path = Path("temp", "downloads", "paper.pdf")
if pdf_path.exists():
    pdf_metadata = processor.process_pdf_metadata(pdf_path)
    print(f"PDF metadata: {pdf_metadata}")

# Example: Process XML metadata (if file exists)
xml_path = Path("temp", "downloads", "paper.xml")
if xml_path.exists():
    xml_metadata = processor.process_xml_metadata(xml_path)
    print(f"XML metadata: {xml_metadata}")
    
    # Normalize metadata
    normalized = processor.normalize_metadata(xml_metadata)
    print(f"Normalized metadata: {normalized}")
else:
    print("Note: No XML file found. Run example 03_repository_search_download.py first to download a paper.")
