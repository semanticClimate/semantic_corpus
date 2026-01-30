# SemanticCorpus Development Plan

**Date:** December 12, 2025  
**Status:** Approved - Ready for Implementation  
**Repository:** Existing semantic_corpus repository

---

## Current State Analysis

### ✅ Already Implemented

1. **Core Infrastructure**
   - `CorpusManager`: Basic corpus management with CRUD operations
   - `RepositoryInterface`: Abstract interface for paper repositories
   - `RepositoryFactory`: Factory pattern for repository creation
   - Repositories: arXiv and Europe PMC implementations
   - CLI: Command-line interface with create, search, download commands
   - Metadata tools: Extractor, processor, validator
   - Test suite: Comprehensive tests with TDD approach

2. **Project Structure**
   - Proper package structure following Python best practices
   - Style guide compliance (absolute imports, empty __init__.py)
   - Configuration: pyproject.toml with dependencies
   - Documentation: README, TESTING.md, session docs

### ❌ Missing Features (From Proposal)

1. **Storage & Structure**
   - BAGIT compliance
   - Structured corpus directory (data/, relations/, analysis/, provenance/)

2. **Transformation**
   - PDF → HTML conversion
   - XML → HTML conversion
   - JATS structuring
   - HTML normalization

3. **Semantification**
   - Semantic ID generation
   - Structure detection
   - Semantic annotation

4. **Keyphrase Extraction**
   - KeyBERT integration
   - YAKE integration
   - TF-IDF extraction
   - Keyphrase indexing

5. **Similarity Analysis**
   - Text similarity computation
   - Similarity matrix generation
   - Feature extraction

6. **Graph & Links**
   - Knowledge graph building
   - Interdocument link creation
   - Graph visualization

7. **Display**
   - DataTable generation
   - HTML rendering

---

## Development Strategy

### Phase 1: Extend Core Infrastructure (Week 1-2)

#### 1.1 Add BAGIT Support
**Files to Create:**
- `semantic_corpus/storage/__init__.py` (empty)
- `semantic_corpus/storage/bagit_manager.py`

**Tasks:**
- Add `bagit` dependency to pyproject.toml
- Create `BagitManager` class for BAGIT bag creation/validation
- Extend `CorpusManager` to support BAGIT structure
- Update corpus directory structure to be BAGIT-compliant

**Integration:**
- Modify `CorpusManager.__init__()` to create BAGIT structure
- Update `add_paper()` to maintain BAGIT manifest

#### 1.2 Extend Corpus Structure
**Files to Modify:**
- `semantic_corpus/core/corpus_manager.py`

**Tasks:**
- Add methods for structured corpus organization:
  - `data/` directory (documents, semantic, metadata, keyphrases, indices)
  - `relations/` directory (similarity_matrix, similarity_graph, related_documents)
  - `analysis/` directory (validation_report, quality_metrics, statistics)
  - `provenance/` directory (ingestion_log, processing_history)

#### 1.3 Ingestion Enhancement
**Files to Create:**
- `semantic_corpus/ingestion/__init__.py` (empty)
- `semantic_corpus/ingestion/pygetpapers_ingester.py`
- `semantic_corpus/ingestion/collection_ingester.py`

**Tasks:**
- Create `PygetpapersIngester` to read `eupmc_result.json`
- Create `CollectionIngester` for collections (IPCC, etc.)
- Integrate with existing `CorpusManager`

---

### Phase 2: Transformation & Semantification (Week 3-4)

#### 2.1 Document Transformation
**Files to Create:**
- `semantic_corpus/transformation/__init__.py` (empty)
- `semantic_corpus/transformation/pdf_to_html.py`
- `semantic_corpus/transformation/xml_to_html.py`
- `semantic_corpus/transformation/html_normalizer.py`

**Tasks:**
- Integrate with amilib for PDF conversion (use existing amilib PDF tools)
- Create XML to HTML converter
- Create HTML normalizer

**Dependencies:**
- Use amilib's `ami_pdf_libs` for PDF processing
- Use lxml for XML/HTML processing

#### 2.2 JATS Processing
**Files to Create:**
- `semantic_corpus/transformation/jats_processor.py`

**Tasks:**
- Use amilib's JATS XSLT resources
- Create JATS to HTML converter
- Add JATS structuring to HTML documents

**Integration:**
- Reference amilib's JATS XSLT files from `amilib/resources/xsl/jats-to-html/`

#### 2.3 Semantification
**Files to Create:**
- `semantic_corpus/semantification/__init__.py` (empty)
- `semantic_corpus/semantification/id_generator.py`
- `semantic_corpus/semantification/structure_detector.py`
- `semantic_corpus/semantification/annotation_adder.py`

**Tasks:**
- Generate semantic IDs for paragraphs/sections
- Detect document structure (headings, paragraphs)
- Add semantic annotations (RDFa, HTML5 semantic elements)

---

### Phase 3: Keyphrase Extraction (Week 5)

#### 3.1 Keyphrase Modules
**Files to Create:**
- `semantic_corpus/keyphrase/__init__.py` (empty)
- `semantic_corpus/keyphrase/extractor.py`
- `semantic_corpus/keyphrase/indexer.py`

**Tasks:**
- Integrate KeyBERT (already used in corpus_module)
- Integrate YAKE
- Use scikit-learn TF-IDF (already available)
- Create keyphrase indexer

**Dependencies to Add:**
```toml
keybert>=0.8.0
yake>=0.4.8
scikit-learn>=1.3.0
```

**Integration:**
- Reference corpus_module's keyphrase extraction methods
- Adapt for semantic_corpus structure

---

### Phase 4: Similarity & Graph (Week 6-7)

#### 4.1 Similarity Analysis
**Files to Create:**
- `semantic_corpus/similarity/__init__.py` (empty)
- `semantic_corpus/similarity/text_similarity.py`
- `semantic_corpus/similarity/feature_extractor.py`
- `semantic_corpus/similarity/similarity_matrix.py`

**Tasks:**
- Implement TF-IDF cosine similarity
- Implement semantic similarity (sentence-transformers)
- Create similarity matrix builder
- Apply similarity thresholds

**Dependencies to Add:**
```toml
sentence-transformers>=2.2.0
scikit-learn>=1.3.0  # Already in dependencies
```

#### 4.2 Graph Building
**Files to Create:**
- `semantic_corpus/graph/__init__.py` (empty)
- `semantic_corpus/graph/graph_builder.py`
- `semantic_corpus/graph/link_creator.py`
- `semantic_corpus/graph/visualizer.py`

**Tasks:**
- Use NetworkX for graph construction (reference amilib's ami_graph.py)
- Create interdocument links based on similarity
- Generate GraphML files
- Create graph visualizations

**Dependencies:**
- NetworkX (check if needed, may be in amilib)
- graphviz (check if needed, may be in amilib)

**Integration:**
- Reference amilib's `ami_graph.py` for graph patterns
- Adapt for document similarity graphs

---

### Phase 5: Display & Validation (Week 8)

#### 5.1 Validation
**Files to Create:**
- `semantic_corpus/validation/__init__.py` (empty)
- `semantic_corpus/validation/conversion_validator.py`
- `semantic_corpus/validation/metadata_validator.py` (extend existing)
- `semantic_corpus/validation/quality_reporter.py`

**Tasks:**
- Extend existing `metadata_validator.py`
- Add conversion quality validation
- Create quality reporting

#### 5.2 Display
**Files to Create:**
- `semantic_corpus/display/__init__.py` (empty)
- `semantic_corpus/display/datatable_generator.py`
- `semantic_corpus/display/html_renderer.py`

**Tasks:**
- Integrate with datatables-module (from amilib)
- Create DataTable generators
- Create HTML renderers for corpus views

**Integration:**
- Use amilib's datatables_module
- Reference corpus_module's DataTable methods

---

## Implementation Details

### Module Structure

```
semantic_corpus/
├── __init__.py                    # Empty (existing)
├── cli.py                         # Extend with new commands (existing)
├── core/                          # Core functionality (existing)
│   ├── corpus_manager.py         # Extend for BAGIT, structure
│   ├── repository_interface.py   # Keep as is
│   ├── repository_factory.py     # Keep as is
│   └── exceptions.py             # Extend with new exceptions
├── repositories/                  # Repository implementations (existing)
│   ├── arxiv.py                  # Keep as is
│   └── europe_pmc.py             # Keep as is
├── tools/                         # Tools (existing)
│   ├── metadata_extractor.py     # Keep as is
│   ├── metadata_processor.py    # Keep as is
│   └── metadata_validator.py     # Extend
├── storage/                       # NEW: Storage management
│   ├── __init__.py
│   ├── bagit_manager.py
│   ├── filesystem_store.py
│   └── manifest_generator.py
├── ingestion/                     # NEW: Document ingestion
│   ├── __init__.py
│   ├── pygetpapers_ingester.py
│   └── collection_ingester.py
├── transformation/                # NEW: Format transformation
│   ├── __init__.py
│   ├── pdf_to_html.py
│   ├── xml_to_html.py
│   ├── jats_processor.py
│   └── html_normalizer.py
├── semantification/               # NEW: Semantic enrichment
│   ├── __init__.py
│   ├── id_generator.py
│   ├── structure_detector.py
│   └── annotation_adder.py
├── keyphrase/                     # NEW: Keyphrase extraction
│   ├── __init__.py
│   ├── extractor.py
│   └── indexer.py
├── similarity/                    # NEW: Similarity analysis
│   ├── __init__.py
│   ├── text_similarity.py
│   ├── feature_extractor.py
│   └── similarity_matrix.py
├── graph/                         # NEW: Knowledge graph
│   ├── __init__.py
│   ├── graph_builder.py
│   ├── link_creator.py
│   └── visualizer.py
├── validation/                    # NEW: Quality validation
│   ├── __init__.py
│   ├── conversion_validator.py
│   ├── metadata_validator.py     # Move from tools/
│   └── quality_reporter.py
└── display/                       # NEW: Display/UI
    ├── __init__.py
    ├── datatable_generator.py
    └── html_renderer.py
```

### Dependencies to Add

Update `pyproject.toml`:

```toml
dependencies = [
    # Existing dependencies...
    "requests>=2.25.0",
    "beautifulsoup4>=4.9.0",
    "lxml>=4.6.0",
    "tqdm>=4.60.0",
    "coloredlogs>=15.0",
    "configargparse>=1.5.0",
    "pyyaml>=6.0.0",
    "pathlib2>=2.3.0; python_version < '3.4'",
    
    # NEW: Storage
    "bagit>=1.8.0",
    
    # NEW: Keyphrase extraction
    "keybert>=0.8.0",
    "yake>=0.4.8",
    "scikit-learn>=1.3.0",
    
    # NEW: Similarity
    "sentence-transformers>=2.2.0",
    
    # NEW: Graph (if not in amilib)
    "networkx>=3.1",
    "graphviz>=0.20.0",
    
    # NEW: Data processing
    "pandas>=2.0.0",
]
```

### CLI Commands to Add

Extend `semantic_corpus/cli.py`:

```python
# New subcommands to add:
- ingest: Ingest documents from pygetpapers or collections
- transform: Transform documents (PDF/XML → HTML)
- semantify: Add semantic structure to documents
- extract-keyphrases: Extract keyphrases from documents
- compute-similarity: Compute document similarity
- build-graph: Build knowledge graph
- validate: Validate corpus quality
- display: Generate DataTables and HTML views
```

---

## Integration with amilib

### Using amilib Modules

1. **PDF Processing**: Import from amilib
   ```python
   # Use amilib's PDF tools
   from amilib.ami_pdf_libs import PdfLib
   ```

2. **HTML Processing**: Import from amilib
   ```python
   from amilib.ami_html import HtmlLib
   ```

3. **Graph Operations**: Reference amilib patterns
   ```python
   # Reference amilib/ami_graph.py patterns
   from amilib.ami_graph import AmiGraph
   ```

4. **DataTables**: Use datatables-module
   ```python
   from datatables_module import Datatables
   ```

### Import Style (Style Guide Compliance)

All imports must be absolute:
```python
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.storage.bagit_manager import BagitManager
from semantic_corpus.keyphrase.extractor import KeyphraseExtractor
```

---

## Testing Strategy

### Test Structure

```
tests/
├── test_corpus_core.py          # Existing - keep
├── test_cli.py                  # Existing - keep
├── test_repository_interface.py # Existing - keep
├── test_metadata_processing.py  # Existing - keep
├── test_integration_live.py     # Existing - keep
├── test_storage.py              # NEW: BAGIT, filesystem
├── test_ingestion.py            # NEW: Ingestion tests
├── test_transformation.py       # NEW: Transformation tests
├── test_semantification.py     # NEW: Semantification tests
├── test_keyphrase.py            # NEW: Keyphrase extraction
├── test_similarity.py           # NEW: Similarity analysis
├── test_graph.py                # NEW: Graph building
├── test_validation.py            # NEW: Validation tests
└── test_display.py               # NEW: Display tests
```

### Test Approach

- Follow TDD: Write tests first
- Use real implementations (no mocks per style guide)
- Test with small corpus (10-20 documents)
- Integration tests for full pipeline
- Performance tests for large corpus (1000+ documents)

---

## Migration Strategy

### Backward Compatibility

1. **Existing CorpusManager**: Extend, don't replace
   - Keep existing methods
   - Add new methods for BAGIT, structure
   - Make BAGIT optional initially

2. **Existing CLI**: Extend with new commands
   - Keep existing commands (create, search, download)
   - Add new commands (ingest, transform, semantify, etc.)

3. **Existing Tests**: Keep all existing tests
   - Ensure new code doesn't break existing tests
   - Add new tests for new functionality

### Gradual Rollout

1. **Phase 1**: Add BAGIT support (optional, backward compatible)
2. **Phase 2**: Add transformation (new feature, doesn't affect existing)
3. **Phase 3**: Add semantification (new feature)
4. **Phase 4**: Add keyphrase extraction (new feature)
5. **Phase 5**: Add similarity and graph (new feature)
6. **Phase 6**: Add display (new feature)

---

## Next Steps

1. **Review this plan** with team
2. **Set up development branch**: Create feature branch for development
3. **Start Phase 1**: Begin with BAGIT support
4. **Iterate**: Follow TDD, commit frequently
5. **Document**: Update docs as we go

---

## Success Criteria

- ✅ All existing tests pass
- ✅ BAGIT-compliant corpus structure
- ✅ Full pipeline from ingestion to display
- ✅ Integration with amilib modules
- ✅ Style guide compliance
- ✅ Comprehensive test coverage
- ✅ Documentation complete

---

*Plan created: December 12, 2025*  
*Status: Ready for Implementation*




