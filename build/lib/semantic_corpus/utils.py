"""Utility functions for semantic_corpus."""

from pathlib import Path
from typing import Optional


def get_project_temp_dir() -> Path:
    """Get the project temp directory."""
    return Path(Path(__file__).parent.parent, "temp")


def get_downloads_dir() -> Path:
    """Get the downloads directory within project temp."""
    downloads_dir = Path(get_project_temp_dir(), "downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    return downloads_dir


def get_corpus_dir() -> Path:
    """Get the corpus directory within project temp."""
    corpus_dir = Path(get_project_temp_dir(), "corpus")
    corpus_dir.mkdir(parents=True, exist_ok=True)
    return corpus_dir


def get_logs_dir() -> Path:
    """Get the logs directory within project temp."""
    logs_dir = Path(get_project_temp_dir(), "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_test_results_dir() -> Path:
    """Get the test results directory within project temp."""
    test_dir = Path(get_project_temp_dir(), "test_results")
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


