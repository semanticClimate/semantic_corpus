"""BAGIT bag management for semantic corpus."""

import bagit
from pathlib import Path
from typing import Dict, Optional, Any


class BagitManager:
    """Manages BAGIT-compliant bags for corpus storage."""

    def __init__(self, bag_dir: Path) -> None:
        """Initialize BAGIT manager with a directory.
        
        Args:
            bag_dir: Path to the bag directory
        """
        self.bag_dir = Path(bag_dir)

    def create_bag(self, metadata: Optional[Dict[str, str]] = None) -> None:
        """Create a BAGIT-compliant bag structure.
        
        Args:
            metadata: Optional dictionary of bag-info.txt metadata
        """
        # Ensure bag directory exists
        self.bag_dir.mkdir(parents=True, exist_ok=True)
        
        # Create data directory (required by BAGIT)
        data_dir = Path(self.bag_dir, "data")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # BAGIT requires at least one file in data/ to be valid
        # Create a placeholder file if data directory is empty
        if not any(data_dir.iterdir()):
            placeholder = Path(data_dir, ".keep")
            placeholder.touch()
        
        # Create bag using bagit library (bag_info parameter, not metadata)
        bag = bagit.make_bag(str(self.bag_dir), bag_info=metadata)
        
        # Verify bag was created (check for required files)
        # bagit.txt and bag-info.txt are always created
        # manifest files depend on checksum algorithm (default is SHA256/SHA512)
        required_files = ["bagit.txt", "bag-info.txt"]
        for file_name in required_files:
            if not Path(self.bag_dir, file_name).exists():
                raise ValueError(f"Failed to create BAGIT bag: missing {file_name}")
        
        # Verify bag is valid
        if not bag.is_valid():
            raise ValueError(f"Failed to create valid BAGIT bag at {self.bag_dir}")

    def validate_bag(self) -> bool:
        """Validate that the directory is a valid BAGIT bag.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            bag = bagit.Bag(str(self.bag_dir))
            return bag.is_valid()
        except (bagit.BagError, OSError):
            return False

    def update_manifest(self) -> None:
        """Update the bag manifest after adding/modifying files."""
        try:
            bag = bagit.Bag(str(self.bag_dir))
            bag.save(manifests=True)
        except bagit.BagError as e:
            raise ValueError(f"Failed to update manifest: {e}")

    def get_bag_info(self) -> Dict[str, str]:
        """Get bag information from bag-info.txt.
        
        Returns:
            Dictionary of bag metadata
        """
        try:
            bag = bagit.Bag(str(self.bag_dir))
            return dict(bag.info)
        except (bagit.BagError, OSError):
            return {}

    def create_structured_directories(self) -> None:
        """Create structured directories for corpus organization.
        
        Creates the following structure:
        - data/documents/{pdf,xml,html}/
        - data/semantic/
        - data/metadata/
        - data/keyphrases/
        - data/indices/
        - relations/
        - analysis/
        - provenance/
        """
        # Ensure data directory exists (required by BAGIT)
        data_dir = Path(self.bag_dir, "data")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Document directories
        Path(data_dir, "documents", "pdf").mkdir(parents=True, exist_ok=True)
        Path(data_dir, "documents", "xml").mkdir(parents=True, exist_ok=True)
        Path(data_dir, "documents", "html").mkdir(parents=True, exist_ok=True)
        
        # Semantic and metadata directories
        Path(data_dir, "semantic").mkdir(parents=True, exist_ok=True)
        Path(data_dir, "metadata").mkdir(parents=True, exist_ok=True)
        Path(data_dir, "keyphrases").mkdir(parents=True, exist_ok=True)
        Path(data_dir, "indices").mkdir(parents=True, exist_ok=True)
        
        # Relations, analysis, and provenance (outside data/ for non-BAGIT files)
        Path(self.bag_dir, "relations").mkdir(parents=True, exist_ok=True)
        Path(self.bag_dir, "analysis").mkdir(parents=True, exist_ok=True)
        Path(self.bag_dir, "provenance").mkdir(parents=True, exist_ok=True)

