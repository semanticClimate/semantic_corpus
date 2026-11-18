# Cluster review — examples

Stepwise Streamlit / library pipeline (see `docs/cluster_filtering_workflow.md`).

## Steps 0–2 in one CLI script (recommended)

Runs the §12 path contract (default query **`AMOC AND India`**, corpus `corpora/amoc_india_2026/`):

| Step | Action |
|------|--------|
| 0 | Search EPMC → download XML → BAGIT |
| 1 | Load / pin active corpus |
| 2 | YAKE phrases (`n=3`) under `<corpus>/phrases/` |

```bash
cd /path/to/semantic_corpus
source venv/bin/activate
pip install yake   # Step 2

# Default --warn: one line per step (Query download / Load corpus / YAKE phrases)
python examples/cluster_review/run_steps_0_2.py --limit 3

# Short progress (≤5 lines/step)
python examples/cluster_review/run_steps_0_2.py --limit 3 --info

# Titles, path samples, JSON
python examples/cluster_review/run_steps_0_2.py --limit 3 --debug

# Pause after each step
python examples/cluster_review/run_steps_0_2.py --limit 3 --pause

# Errors only
python examples/cluster_review/run_steps_0_2.py --error --from-step 1

# Resume / re-YAKE
python examples/cluster_review/run_steps_0_2.py --from-step 1
python examples/cluster_review/run_steps_0_2.py --from-step 2 --clear-phrases
```

Streamlit remains optional for later UI testing:
`streamlit run apps/cluster_review/app.py`

## Step 0 — Query → download → optional BAGIT

**Library API:** `semantic_corpus.cluster_review.create_corpus_from_query`

**CLI-style example (mocked network not required if you use a tiny live limit):**

```bash
cd /path/to/semantic_corpus
source venv/bin/activate

# Offline-safe unit tests
pytest tests/test_cluster_review_step0.py -v

# Live example (Europe PMC; keep limit small)
python examples/cluster_review/step0_create_from_query.py \
  --query '("marine heatwave") AND OPEN_ACCESS:Y AND HAS_FT:Y' \
  --query-name step0_live_demo \
  --limit 3 \
  --create-bagit
```

**Streamlit (Step 0 only in the shared app shell):**

```bash
pip install streamlit   # if needed
streamlit run apps/cluster_review/app.py
```

Use the **Query → BAGIT** stage. Later stages are visible but locked until implemented.

## Step 1 — Load existing BAGIT

```bash
# List demo corpora present on disk
python examples/cluster_review/step1_load_bagit.py --list-demos

# Load a demo (or any path)
python examples/cluster_review/step1_load_bagit.py --demo step0_live_demo
python examples/cluster_review/step1_load_bagit.py --corpus-dir corpora/aqi_india_pilot

# Unit tests
pytest tests/test_cluster_review_step1.py -v
```

In Streamlit, open stage **1. Load BAGIT**, pick a demo or path, click **Load BAGIT**.

## Update BAGIT with additional files (PDF)

Fetch missing PDFs into an existing bag (any time after Step 1). Skips valid PDFs; rejects HTML/error stubs.

```bash
python examples/cluster_review/update_corpus_files.py \
  --corpus-dir corpora/amoc_india_2026 --formats pdf

# Force re-download
python examples/cluster_review/update_corpus_files.py \
  --corpus-dir corpora/amoc_india_2026 --formats pdf --force

pytest tests/test_cluster_review_update_corpus.py -v
```

In Streamlit: sidebar **Update corpus files (PDF)** when a corpus is active, or the same button on Step 1.

## Step 2 — YAKE phrases (n=3)

Requires `yake` in the **same** Python you run with:

```bash
# Prefer the project venv
./venv/bin/python -m pip install 'semantic_corpus[cluster_review]'
# or, for system python3:
python3 -m pip install yake
```

```bash
# Extract (caches under <corpus>/phrases/)
python examples/cluster_review/step2_extract_yake.py --demo step0_live_demo

# Force re-extract
python examples/cluster_review/step2_extract_yake.py --corpus-dir corpora/aqi_india_pilot --force

# Clear phrase caches (clean slate), or clear then extract
python examples/cluster_review/step2_extract_yake.py --demo step0_live_demo --clear-cache
python examples/cluster_review/step2_extract_yake.py --demo step0_live_demo --clear-and-extract

# Unit tests
pytest tests/test_cluster_review_step2.py -v
```

In Streamlit, open stage **2. Phrases (YAKE)** after an active corpus (Step 0/1), then **Extract YAKE phrases**, **Use cached phrases**, or **Clear all caches**.
