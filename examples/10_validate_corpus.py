#!/usr/bin/env python3
"""
Example 10: Validate corpus integrity and generate report.

This example demonstrates how to validate a BAGIT corpus and generate a validation report.
"""

from pathlib import Path
from semantic_corpus.storage.bagit_manager import BagitManager
import json
from datetime import datetime

def validate_corpus(corpus_dir: Path):
    """Validate corpus integrity and generate report."""
    bagit_mgr = BagitManager(corpus_dir)
    
    is_valid = bagit_mgr.validate_bag()
    bag_info = bagit_mgr.get_bag_info()
    
    report = {
        "validation_date": datetime.now().isoformat(),
        "corpus_path": str(corpus_dir),
        "is_valid": is_valid,
        "bag_info": bag_info
    }
    
    report_path = Path(corpus_dir, "analysis", "validation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return is_valid

# Run validation
corpus_dir = Path("corpora", "my_research")
if corpus_dir.exists():
    if validate_corpus(corpus_dir):
        print("Corpus validation passed")
    else:
        print("WARNING: Corpus validation failed")
else:
    print(f"Corpus directory {corpus_dir} does not exist")
    print("Create a corpus first using example 01_create_corpus.py")
