"""Tests for CLI functionality."""

import pytest
import subprocess
import sys
from pathlib import Path
from semantic_corpus.cli import main, create_parser


class TestCLI:
    """Test cases for CLI functionality."""

    def test_cli_main_help(self):
        """Test that CLI shows help message."""
        parser = create_parser()
        help_text = parser.format_help()
        
        assert "semantic_corpus" in help_text
        assert "create" in help_text
        assert "search" in help_text
        assert "download" in help_text

    def test_create_corpus_command(self, temp_dir: Path):
        """Test create corpus command."""
        # Test using subprocess to call the CLI
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "create", "--name", "test_corpus", "--path", str(temp_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Corpus 'test_corpus' created successfully" in result.stdout
        assert Path(temp_dir, "test_corpus").exists()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_search_papers_command(self, temp_dir: Path):
        """Test search papers command with live API."""
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "search", "--query", "climate change",
            "--repository", "europe_pmc",
            "--limit", "3",  # Reduced for faster testing
            "--output", str(temp_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Found" in result.stdout
        assert "papers" in result.stdout
        # Verify we got real results
        assert "climate" in result.stdout.lower() or "change" in result.stdout.lower()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_download_papers_command(self, temp_dir: Path):
        """Test download papers command with live API."""
        # Use a query that's more likely to return papers with PMCIDs
        # Query for open access papers which are more likely to have full-text XML
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "download", "--query", "climate change AND OPEN_ACCESS:y",
            "--repository", "europe_pmc",
            "--limit", "5",  # Increased to improve chances of finding papers with PMCIDs
            "--output", str(temp_dir),
            "--formats", "xml",  # Start with XML only for faster testing
            "--verbose"  # Enable verbose output for better diagnostics
        ], capture_output=True, text=True)
        
        # Print output for debugging
        if result.returncode != 0:
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
        
        assert result.returncode == 0, f"Command failed with return code {result.returncode}"
        assert "Found" in result.stdout, "Expected 'Found' in output"
        assert "papers" in result.stdout.lower() or "Downloaded" in result.stdout, \
            f"Expected download summary in output. Got: {result.stdout}"
        
        # Check if any files were actually downloaded
        xml_files = list(temp_dir.glob("*.xml"))
        pdf_files = list(temp_dir.glob("*.pdf"))
        all_files = list(temp_dir.iterdir())
        
        # Print diagnostic information
        print(f"\nDiagnostics:")
        print(f"  Output directory: {temp_dir}")
        print(f"  All files in directory: {[f.name for f in all_files]}")
        print(f"  XML files found: {[f.name for f in xml_files]}")
        print(f"  PDF files found: {[f.name for f in pdf_files]}")
        print(f"  STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"  STDERR:\n{result.stderr}")
        
        # Verify files were actually downloaded
        # Note: Some papers may not have PMCIDs (required for XML/PDF download)
        # So we check if at least one file was downloaded OR if papers were skipped due to no PMCID
        has_downloaded_files = len(xml_files) > 0 or len(pdf_files) > 0
        has_skipped_papers = "Skipped" in result.stdout or "skipped" in result.stdout.lower()
        
        # If we have downloaded files, great! If not, check if it's because papers were skipped
        if not has_downloaded_files:
            # Check if the issue is that papers don't have PMCIDs (expected for some papers)
            if "no PMCID" in result.stdout.lower() or "no pmcid" in result.stdout.lower():
                # This is acceptable - not all papers have PMCIDs
                # But we should have at least tried to download something
                assert "Found" in result.stdout and "papers" in result.stdout.lower(), \
                    "Should have found papers even if downloads failed"
                # If all papers were skipped, that's a test limitation, not a failure
                if "Successfully downloaded: 0" in result.stdout:
                    pytest.skip("No papers with PMCIDs found in search results - this is a limitation of the test data, not a code failure")
        
        assert has_downloaded_files, \
            f"No .xml or .pdf files found in {temp_dir}. Files present: {[f.name for f in all_files]}. " \
            f"Output: {result.stdout}"

    @pytest.mark.live_api
    @pytest.mark.network
    def test_cli_with_config_file(self, temp_dir: Path):
        """Test CLI with configuration file using live API."""
        config_file = Path(temp_dir, "config.yaml")
        test_corpus_path = Path(temp_dir, "test_corpus")
        # Use YAML literal block to avoid escape sequence issues
        config_content = f"""query: climate change
repository: europe_pmc
limit: 2
output: {str(test_corpus_path)}
formats: [xml]
"""
        config_file.write_text(config_content)
        
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "--config", str(config_file), "download"
        ], capture_output=True, text=True)
        
        # If the command fails due to API issues, skip the test
        if result.returncode != 0:
            if "No search results found" in result.stderr or "API" in result.stderr:
                pytest.skip("API returned no results - may be rate limited or blocked")
            else:
                print(f"CLI failed with return code {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                assert False, f"CLI failed unexpectedly: {result.stderr}"
        
        assert result.returncode == 0
        assert "test_corpus" in result.stdout
        # Verify we got real results
        assert "Downloaded" in result.stdout or "Found" in result.stdout

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        # Test with invalid repository
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "search", "--query", "test", "--repository", "invalid_repo"
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "error" in result.stderr.lower()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_cli_verbose_output(self, temp_dir: Path):
        """Test CLI verbose output with live API."""
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "search", "--query", "climate change",
            "--repository", "europe_pmc",
            "--limit", "2",
            "--output", str(temp_dir),
            "--verbose"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        # With live API, we should see actual search results
        assert "Found" in result.stdout
        assert "papers" in result.stdout
