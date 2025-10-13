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
        assert (temp_dir / "test_corpus").exists()

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
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "download", "--query", "climate change",
            "--repository", "europe_pmc",
            "--limit", "2",  # Reduced for faster testing
            "--output", str(temp_dir),
            "--formats", "xml"  # Start with XML only for faster testing
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Downloaded" in result.stdout
        assert "papers" in result.stdout
        # Verify files were actually downloaded
        assert any((temp_dir / f).exists() for f in temp_dir.iterdir() if f.suffix in ['.xml', '.pdf'])

    @pytest.mark.live_api
    @pytest.mark.network
    def test_cli_with_config_file(self, temp_dir: Path):
        """Test CLI with configuration file using live API."""
        config_file = temp_dir / "config.yaml"
        config_content = f"""
query: "climate change"
repository: "europe_pmc"
limit: 2
output: "{temp_dir / "test_corpus"}"
formats: ["xml"]
"""
        config_file.write_text(config_content)
        
        result = subprocess.run([
            sys.executable, "-m", "semantic_corpus.cli",
            "--config", str(config_file), "download"
        ], capture_output=True, text=True)
        
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
