# SemanticCorpus Examples

This directory contains executable example scripts demonstrating how to use SemanticCorpus.

## Overview

These examples are extracted from the documentation (`docs/overview.md`) and made into standalone, executable scripts. Each example demonstrates a specific feature or workflow.

## Prerequisites

1. **Install the package**:
   ```bash
   pip install -e .
   ```

2. **Ensure you have network access** (for repository examples):
   - Examples that download papers require internet connection
   - Europe PMC and arXiv APIs must be accessible

## Running Examples

### Basic Examples (No Network Required)

These examples work with local files and directories:

1. **Create a corpus**:
   ```bash
   python examples/01_create_corpus.py
   ```

2. **BAGIT operations**:
   ```bash
   python examples/02_bagit_operations.py
   ```

3. **List papers**:
   ```bash
   python examples/05_list_papers.py
   ```

4. **Get paper metadata**:
   ```bash
   python examples/06_get_paper_metadata.py
   ```

5. **Search papers**:
   ```bash
   python examples/07_search_papers.py
   ```

6. **Corpus statistics**:
   ```bash
   python examples/08_corpus_statistics.py
   ```

7. **Validate corpus**:
   ```bash
   python examples/10_validate_corpus.py
   ```

### Repository Examples (Network Required)

These examples interact with live APIs:

1. **Repository search and download**:
   ```bash
   python examples/03_repository_search_download.py
   ```

2. **Complete ingestion workflow**:
   ```bash
   python examples/09_ingest_from_europe_pmc.py
   ```

### Metadata Processing

1. **Process metadata from files**:
   ```bash
   python examples/04_metadata_processing.py
   ```
   Note: Requires downloaded files. Run example 03 first.

## Example Descriptions

### 01_create_corpus.py
Creates a new corpus with BAGIT support, adds a sample paper, and lists papers.

### 02_bagit_operations.py
Demonstrates BAGIT bag creation, validation, and retrieving bag information.

### 03_repository_search_download.py
Searches Europe PMC for papers and downloads XML files.

### 04_metadata_processing.py
Processes metadata from PDF and XML files, normalizes metadata.

### 05_list_papers.py
Lists all papers in an existing corpus.

### 06_get_paper_metadata.py
Retrieves and displays metadata for a specific paper.

### 07_search_papers.py
Searches papers in corpus by title or abstract.

### 08_corpus_statistics.py
Retrieves and displays corpus statistics.

### 09_ingest_from_europe_pmc.py
Complete workflow: search → download → process → add to corpus.

### 10_validate_corpus.py
Validates corpus integrity and generates validation report.

## Customizing Examples

All examples use default paths that you can customize:

- **Corpus directories**: Change `Path("corpora", "my_research")` to your desired location
- **Download directories**: Change `Path("temp", "downloads")` to your preferred location
- **Paper IDs**: Modify paper IDs to match your corpus
- **Queries**: Adjust search queries to find papers relevant to your research

## Example Workflow

For a complete workflow, run examples in this order:

1. `01_create_corpus.py` - Create your corpus
2. `03_repository_search_download.py` - Download some papers
3. `09_ingest_from_europe_pmc.py` - Ingest papers into corpus
4. `05_list_papers.py` - List papers in corpus
5. `07_search_papers.py` - Search your corpus
6. `08_corpus_statistics.py` - View statistics
7. `10_validate_corpus.py` - Validate integrity

## Troubleshooting

### "Corpus directory does not exist"
- Run `01_create_corpus.py` first to create a corpus

### "No papers found"
- Run `09_ingest_from_europe_pmc.py` to add papers to your corpus

### "Network errors"
- Check your internet connection
- Some examples require network access for repository APIs
- Try running examples marked as "No Network Required" first

### "File not found"
- Some examples depend on files created by other examples
- Check the example descriptions for dependencies
- Run examples in the suggested order

## Notes

- Examples create files in `corpora/` and `temp/` directories
- These directories are not committed to git (see `.gitignore`)
- You can safely delete and recreate them
- Examples use small limits (e.g., `limit=5`) for faster execution
- Adjust limits and queries as needed for your use case

## Related Documentation

- **Overview**: `docs/overview.md` - Complete documentation with all examples
- **Development Plan**: `docs/development_plan.md` - Feature roadmap
- **Testing Guide**: `TESTING.md` - How to run tests
