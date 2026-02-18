#!/usr/bin/env python3
"""
Example 2: BAGIT operations - create bag and validate integrity.

This example demonstrates how to create a BAGIT-compliant bag and validate it.
"""

from pathlib import Path
from semantic_corpus.storage.bagit_manager import BagitManager

bag_dir = Path("corpora", "my_research")
bagit_mgr = BagitManager(bag_dir)

# Create bag with metadata
metadata = {
    "Source-Organization": "My Research Lab",
    "Contact-Name": "Jane Doe",
    "Contact-Email": "jane@example.com"
}
bagit_mgr.create_bag(metadata=metadata)

# Validate bag
is_valid = bagit_mgr.validate_bag()
print(f"Bag is valid: {is_valid}")

# Get bag information
bag_info = bagit_mgr.get_bag_info()
print(f"Bag info: {bag_info}")
