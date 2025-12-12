"""Tests for storage management functionality."""

import pytest
from pathlib import Path
from semantic_corpus.storage.bagit_manager import BagitManager
from semantic_corpus.core.exceptions import CorpusError


class TestBagitManager:
    """Test cases for BagitManager class."""

    def test_bagit_manager_initialization(self, temp_dir: Path):
        """Test that BagitManager can be initialized with a directory."""
        bagit_manager = BagitManager(temp_dir)
        assert bagit_manager.bag_dir == temp_dir

    def test_create_bag_structure(self, temp_dir: Path):
        """Test creating a BAGIT-compliant bag structure."""
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag()
        
        # Check BAGIT required files
        assert Path(temp_dir, "bagit.txt").exists()
        assert Path(temp_dir, "bag-info.txt").exists()
        # bagit library creates SHA256/SHA512 manifests by default, not MD5
        # Check that at least one manifest file exists
        manifest_files = [
            Path(temp_dir, "manifest-md5.txt"),
            Path(temp_dir, "manifest-sha256.txt"),
            Path(temp_dir, "manifest-sha512.txt"),
        ]
        assert any(mf.exists() for mf in manifest_files), "No manifest file found"
        assert Path(temp_dir, "data").exists()
        assert Path(temp_dir, "data").is_dir()

    def test_create_bag_with_metadata(self, temp_dir: Path):
        """Test creating a bag with custom metadata."""
        metadata = {
            "Source-Organization": "Test Organization",
            "Organization-Address": "123 Test St",
            "Contact-Name": "Test User",
            "Contact-Email": "test@example.com",
        }
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag(metadata=metadata)
        
        # Check bag-info.txt contains metadata
        bag_info = Path(temp_dir, "bag-info.txt")
        assert bag_info.exists()
        content = bag_info.read_text()
        assert "Source-Organization: Test Organization" in content

    def test_validate_bag(self, temp_dir: Path):
        """Test validating an existing bag."""
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag()
        
        # Validation should pass for a valid bag
        is_valid = bagit_manager.validate_bag()
        assert is_valid is True

    def test_add_file_to_bag(self, temp_dir: Path):
        """Test adding a file to the bag data directory."""
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag()
        
        # Create a test file
        test_file = Path(temp_dir, "data", "test.txt")
        test_file.write_text("test content")
        
        # Update manifest
        bagit_manager.update_manifest()
        
        # Check manifest includes the file (check any manifest file that exists)
        manifest_files = [
            Path(temp_dir, "manifest-md5.txt"),
            Path(temp_dir, "manifest-sha256.txt"),
            Path(temp_dir, "manifest-sha512.txt"),
        ]
        manifest = next((mf for mf in manifest_files if mf.exists()), None)
        assert manifest is not None, "No manifest file found after update"
        content = manifest.read_text()
        assert "data/test.txt" in content

    def test_get_bag_info(self, temp_dir: Path):
        """Test retrieving bag information."""
        metadata = {
            "Source-Organization": "Test Org",
            "Bag-Size": "1 MB",
        }
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag(metadata=metadata)
        
        bag_info = bagit_manager.get_bag_info()
        
        assert "Source-Organization" in bag_info
        assert bag_info["Source-Organization"] == "Test Org"
        assert "Bag-Size" in bag_info

    def test_create_structured_directories(self, temp_dir: Path):
        """Test creating structured corpus directories."""
        bagit_manager = BagitManager(temp_dir)
        bagit_manager.create_bag()
        bagit_manager.create_structured_directories()
        
        # Check all required directories exist
        assert Path(temp_dir, "data", "documents").exists()
        assert Path(temp_dir, "data", "documents", "pdf").exists()
        assert Path(temp_dir, "data", "documents", "xml").exists()
        assert Path(temp_dir, "data", "documents", "html").exists()
        assert Path(temp_dir, "data", "semantic").exists()
        assert Path(temp_dir, "data", "metadata").exists()
        assert Path(temp_dir, "data", "keyphrases").exists()
        assert Path(temp_dir, "data", "indices").exists()
        assert Path(temp_dir, "relations").exists()
        assert Path(temp_dir, "analysis").exists()
        assert Path(temp_dir, "provenance").exists()

    def test_validate_invalid_bag(self, temp_dir: Path):
        """Test validating an invalid bag (missing required files)."""
        # Create directory but not a valid bag
        Path(temp_dir, "data").mkdir()
        
        bagit_manager = BagitManager(temp_dir)
        
        # Validation should fail
        is_valid = bagit_manager.validate_bag()
        assert is_valid is False

