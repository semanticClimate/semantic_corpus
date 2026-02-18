# semantic_corpus
*creation and management of personal scientific corpora, often created by downloading from Open repositories*

## About
`semantic_corpus` is a Python tool designed for researchers to create and manage personal scientific corpora. It automates the process of searching, downloading, and organizing scientific papers from open-access repositories.

## Features

- **Multi-Repository Search**: Seamlessly search across Europe PMC and arXiv.
- **Automated Downloads**: Bulk download papers in multiple formats (PDF, XML, etc.).
- **Corpus Management**: Organize your research into structured, searchable corpora.
- **BAGIT Support**: Optional long-term preservation using the BAGIT standard.
- **Flexible Configuration**: Use YAML files to manage complex search and download tasks.

## Tech Stack

- **Python 3.8+**
- **Libraries**: `requests`, `beautifulsoup4`, `lxml`, `tqdm`, `configargparse`, `pyyaml`.

## Installation

```bash
# Clone the repository
git clone https://github.com/semanticClimate/semantic_corpus.git
cd semantic_corpus

# Install the package
pip install .
```

For development and testing:
```bash
pip install -e ".[dev]"
```
## Usage
### Quick Start
```bash
# Create a new corpus
semantic_corpus create --name "MyResearch"

# Search and download papers
semantic_corpus download --query "climate change" --repository europe_pmc --limit 5 --formats "pdf,xml"
```

## Command Reference

The `semantic_corpus` CLI provides several subcommands. Use `semantic_corpus [command] --help` for more details.

### Global Optional Arguments
- `-c, --config PATH`: Path to a YAML configuration file.
- `-v, --verbose`: Enable verbose output for debugging.

---
### 1. `create`
Initialize a new structured corpus directory.

| Flag | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--name` | `-n` | **(Required)** The name of the corpus. | N/A |
| `--path` | `-p` | Specific directory path for the corpus. | `temp/corpus/{name}` |
| `--verbose`| `-v` | Enable verbose output. | `False` |

---

### 2. `search`
Search for papers without downloading them. Results are saved to a JSON file.

| Flag | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--query` | `-q` | **(Required)** Search query string. | N/A |
| `--repository`| `-r` | Data source (`europe_pmc`, `arxiv`). | `europe_pmc` |
| `--limit` | `-l` | Maximum number of results to return. | `10` |
| `--output` | `-o` | Directory to save search results. | `temp/downloads` |
| `--verbose` | `-v` | Enable verbose output. | `False` |

---

### 3. `download`
Search for and download papers in specified formats.

| Flag | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--query` | `-q` | **(Required)** Search query string. | N/A |
| `--repository`| `-r` | Data source (`europe_pmc`, `arxiv`). | `europe_pmc` |
| `--limit` | `-l` | Maximum number of results to return. | `10` |
| `--formats` | `-f` | Comma-separated file formats (`pdf`, `xml`). | `xml,pdf` |
| `--output` | `-o` | Directory to save downloaded files. | `temp/downloads` |
| `--verbose` | `-v` | Enable verbose output. | `False` |

## Configuration (YAML)

Manage your tasks efficiently using a configuration file:

```yaml
# config.yaml
query: "artificial intelligence"
repository: "arxiv"
limit: 50
formats: 
  - pdf
  - xml
output: "./my_downloads"
```

Run with:
```bash
semantic_corpus download --config config.yaml
```

## Project Structure

```text
semantic_corpus/
├── core/           # Corpus management and repository interfaces
├── repositories/   # Implementation for arXiv and Europe PMC
├── storage/        # BAGIT and storage handlers
├── cli.py          # Command-line interface
└── utils.py        # Shared utility functions
```

## Development

We use `pytest` for testing.

```bash
# Run all tests
pytest
```


