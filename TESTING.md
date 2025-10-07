# Testing Guide for semantic_corpus

This document explains how to run the tests for the semantic_corpus project, which uses live APIs and real downloads.

## Test Categories

### 1. Unit Tests (No Network Required)
These tests don't require network access and run quickly:
```bash
pytest tests/test_corpus_core.py tests/test_metadata_processing.py -m "not live_api"
```

### 2. Live API Tests (Network Required)
These tests interact with real repositories and download actual papers:
```bash
# Run all live API tests
pytest -m "live_api"

# Run only Europe PMC tests
pytest tests/test_repository_interface.py::TestEuropePMCRepository -m "live_api"

# Run only arXiv tests
pytest tests/test_repository_interface.py::TestArxivRepository -m "live_api"
```

### 3. Integration Tests (Full Workflow)
These tests demonstrate complete workflows with real data:
```bash
pytest tests/test_integration_live.py
```

### 4. CLI Tests (Live APIs)
These tests verify the command-line interface with real repositories:
```bash
pytest tests/test_cli.py -m "live_api"
```

## Running All Tests

### With Live APIs (Recommended)
```bash
# Run all tests including live API tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=semantic_corpus
```

### Without Live APIs (Fast, but limited)
```bash
# Skip live API tests for faster execution
pytest -m "not live_api"
```

## Test Configuration

### Environment Variables
- `SEMANTIC_CORPUS_TEST_TIMEOUT`: Set timeout for API calls (default: 30 seconds)
- `SEMANTIC_CORPUS_TEST_LIMIT`: Set maximum number of papers to download (default: 3)

### Test Markers
- `@pytest.mark.live_api`: Tests that use live APIs
- `@pytest.mark.network`: Tests that require network access
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Tests that take longer to run

## What the Live API Tests Do

### Repository Tests
1. **Search Tests**: Query real repositories (Europe PMC, arXiv) for papers
2. **Metadata Tests**: Retrieve actual paper metadata
3. **Download Tests**: Download real papers (XML, PDF) to temporary directories

### Integration Tests
1. **Full Workflow**: Search → Download → Add to Corpus → Search in Corpus
2. **Statistics**: Test corpus statistics with real downloaded papers
3. **Error Handling**: Test error scenarios with live APIs

### CLI Tests
1. **Search Command**: Test `semantic_corpus search` with real repositories
2. **Download Command**: Test `semantic_corpus download` with real papers
3. **Config File**: Test configuration file support

## Expected Test Results

### Live API Tests Should:
- ✅ Successfully search for papers using real queries
- ✅ Download actual papers (XML/PDF files)
- ✅ Verify downloaded files exist and have content
- ✅ Add real papers to corpus and retrieve them
- ✅ Perform searches within the corpus

### Test Data
- **Query**: "climate change" (reliable, returns results)
- **Limit**: 2-3 papers per test (fast, sufficient for testing)
- **Formats**: XML for Europe PMC, PDF for arXiv
- **Categories**: cs.AI for arXiv (reliable results)

## Troubleshooting

### Network Issues
If tests fail due to network issues:
```bash
# Run without live API tests
pytest -m "not live_api"
```

### API Rate Limits
If you hit rate limits:
```bash
# Run tests with delays
pytest --tb=short -x
```

### Missing Dependencies
Install required packages:
```bash
pip install -e ".[dev]"
```

## Test Output

Successful live API tests will show:
- Real paper titles and abstracts
- Downloaded file paths and sizes
- Corpus statistics with actual data
- Search results from real repositories

This demonstrates that the semantic_corpus system works with real scientific data and can be used for actual research workflows.
