# Semantic Corpus Temp Directory

This directory contains all temporary outputs and working files for the semantic_corpus project.

## Directory Structure

```
temp/
├── corpus/           # Corpus storage directories
│   └── {corpus_name}/    # Individual corpus directories
├── downloads/        # Downloaded papers and search results
│   ├── search_results.json
│   ├── {paper_id}.xml
│   └── {paper_id}.pdf
├── logs/            # Application logs
├── test_results/    # Test output and temporary test files
└── README.md        # This file
```

## Usage

- **Corpus**: Created when using `semantic_corpus create` command without specifying a path
- **Downloads**: Used as default output directory for `search` and `download` commands
- **Logs**: For application logging (future use)
- **Test Results**: Temporary files created during test execution

## Cleanup

This directory can be safely deleted to clean up temporary files. The application will recreate necessary directories as needed.

## Default Behavior

When no output directory is specified:
- CLI commands use `temp/downloads/` for file outputs
- Corpus creation uses `temp/corpus/{name}/` for new corpora
- Tests use `temp/test_results/` for temporary test files
