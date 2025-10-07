"""Tests for CLI functionality."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from semantic_corpus.cli import main, create_corpus, search_papers, download_papers


class TestCLI:
    """Test cases for CLI functionality."""

    def test_cli_main_help(self):
        """Test that CLI shows help message."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        
        assert result.exit_code == 0
        assert "semantic_corpus" in result.output
        assert "create" in result.output
        assert "search" in result.output
        assert "download" in result.output

    def test_create_corpus_command(self, temp_dir: Path):
        """Test create corpus command."""
        runner = CliRunner()
        result = runner.invoke(
            create_corpus,
            ["--name", "test_corpus", "--path", str(temp_dir)]
        )
        
        assert result.exit_code == 0
        assert "Corpus created successfully" in result.output
        assert (temp_dir / "test_corpus").exists()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_search_papers_command(self, temp_dir: Path):
        """Test search papers command with live API."""
        runner = CliRunner()
        result = runner.invoke(
            search_papers,
            [
                "--query", "climate change",
                "--repository", "europe_pmc",
                "--limit", "3",  # Reduced for faster testing
                "--output", str(temp_dir)
            ]
        )
        
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "papers" in result.output
        # Verify we got real results
        assert "climate" in result.output.lower() or "change" in result.output.lower()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_download_papers_command(self, temp_dir: Path):
        """Test download papers command with live API."""
        runner = CliRunner()
        result = runner.invoke(
            download_papers,
            [
                "--query", "climate change",
                "--repository", "europe_pmc",
                "--limit", "2",  # Reduced for faster testing
                "--output", str(temp_dir),
                "--formats", "xml"  # Start with XML only for faster testing
            ]
        )
        
        assert result.exit_code == 0
        assert "Downloaded" in result.output
        assert "papers" in result.output
        # Verify files were actually downloaded
        assert any((temp_dir / f).exists() for f in temp_dir.iterdir() if f.suffix in ['.xml', '.pdf'])

    @pytest.mark.live_api
    @pytest.mark.network
    def test_cli_with_config_file(self, temp_dir: Path):
        """Test CLI with configuration file using live API."""
        config_file = temp_dir / "config.yaml"
        config_content = """
query: "climate change"
repository: "europe_pmc"
limit: 2
output: "climate_corpus"
formats: ["xml"]
"""
        config_file.write_text(config_content)
        
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", str(config_file), "download"]
        )
        
        assert result.exit_code == 0
        assert "climate_corpus" in result.output
        # Verify we got real results
        assert "Downloaded" in result.output or "Found" in result.output

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        runner = CliRunner()
        
        # Test with invalid repository
        result = runner.invoke(
            search_papers,
            ["--query", "test", "--repository", "invalid_repo"]
        )
        
        assert result.exit_code != 0
        assert "error" in result.output.lower()

    @pytest.mark.live_api
    @pytest.mark.network
    def test_cli_verbose_output(self, temp_dir: Path):
        """Test CLI verbose output with live API."""
        runner = CliRunner()
        result = runner.invoke(
            search_papers,
            [
                "--query", "climate change",
                "--repository", "europe_pmc",
                "--limit", "2",
                "--output", str(temp_dir),
                "--verbose"
            ]
        )
        
        assert result.exit_code == 0
        # With live API, we should see actual search results
        assert "Found" in result.output
        assert "papers" in result.output
