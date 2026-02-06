# Test Resources Directory

This directory contains static test input files used by the test suite.

## Purpose

Test input files are stored here to ensure:
- **Portability**: Files are version-controlled and available to all developers
- **Consistency**: Same test files used across all environments
- **Maintainability**: Easy to update test files when needed
- **Style Guide Compliance**: Test inputs are in the `tests/` tree as required

## Files

- `sample.pdf` - Sample PDF file for testing PDF metadata extraction
- `sample.xml` - Sample XML file for testing XML metadata extraction
- `sample.json` - Sample JSON file for testing JSON metadata extraction
- `sample.txt` - Sample text file for testing unsupported format error handling

## Usage

These files are accessed via pytest fixtures defined in `tests/conftest.py`:
- `sample_pdf_path` - Returns path to `sample.pdf`
- `sample_xml_path` - Returns path to `sample.xml`

For other files, tests reference them directly using:
```python
sample_file = Path(Path(__file__).parent, "resources", "sample.json")
```

## Note

Test **outputs** (temporary files created during tests) are stored in `temp_dir` fixtures, which create temporary directories. Only **input** files are stored in this directory.
