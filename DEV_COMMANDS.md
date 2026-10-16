# Developer Quick Start & Useful Commands Guide

This guide summarizes the essential commands for working on the `semantic_corpus` repository, setting up your environment, linting/formatting with Ruff, and using pre-commit hooks.

---

## 1. 🚀 First-Time Setup (Onboarding)

We provide setup scripts that automatically create the virtual environment (`.venv`), install all project dependencies (including development and linting tools), and configure Git pre-commit hooks.

### On Windows (PowerShell):
```powershell
.\setup.ps1
```

### On macOS / Linux (Bash):
```bash
bash setup.sh
```

*(Alternatively, manual install inside an existing venv)*:
```bash
pip install -e ".[dev]"
pre-commit install
```

---

## 2. ⚡ Activating the Virtual Environment

### Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If you see an execution policy error in PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once).*

### macOS / Linux:
```bash
source .venv/bin/activate
```

---

## 3. 🧹 Code Quality with Ruff (Linter & Formatter)

Ruff handles both code formatting (replacing Black) and code quality/linting (replacing Flake8 and isort).

| Task | Command | Note |
| :--- | :--- | :--- |
| **Check code for errors** | `ruff check .` | Scans the repo for bugs, unused imports, PEP 8 errors |
| **Auto-fix errors** | `ruff check --fix .` | Automatically fixes imports, whitespace, and safe rules |
| **Format all code** | `ruff format .` | Formats all `.py` files according to project style |
| **Verify formatting** | `ruff format --check .` | Checks without modifying (useful in CI or before committing) |
| **Target specific folder/file** | `ruff check semantic_corpus/` | Runs checks on a specific path |

> **Tip for Windows:** If `ruff` command is not recognized, run it via Python module:
> ```powershell
> python -m ruff check .
> python -m ruff check --fix .
> python -m ruff format .
> ```

---

## 4. 🪝 Pre-commit Hooks

Pre-commit runs automatically every time you run `git commit`. It ensures no malformed or broken code is committed to the repository.

* **Normal Workflow:**
  1. Make your changes in code.
  2. Stage your files: `git add .`
  3. Commit: `git commit -m "Your commit message"`
  4. If Ruff modifies or formats any files, simply stage the updated files with `git add .` and run `git commit` again.

* **Run pre-commit manually on all files:**
  ```bash
  pre-commit run --all-files
  ```

* **Emergency bypass (use only if strictly necessary):**
  ```bash
  git commit -m "Quick fix" --no-verify
  ```

---

## 5. 🧪 Running Tests

```bash
# Run full test suite (skips live APIs & slow tests by default)
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_corpus_manager.py

# Run with test coverage report
pytest --cov=semantic_corpus
```

---

## 6. 💻 Editor Setup (VS Code)

To make VS Code format and organize imports automatically every time you save a file (`Ctrl + S` / `Cmd + S`):

1. Install the official **Ruff** extension (`charliermarsh.ruff`) from the VS Code Marketplace.
2. Add the following to your workspace `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

---

## 7. 💡 FAQs & Common Tricks

* **How do I ignore a rule on a specific line?**
  Add `# noqa: <RULE_CODE>` at the end of the line:
  ```python
  import unused_module  # noqa: F401
  ```

* **Why did `ruff check --fix` leave some errors unfixed?**
  Ruff distinguishes between **safe fixes** (applied automatically) and **unsafe fixes** (which might change program behavior, such as removing an unused assigned variable). If you want Ruff to apply unsafe fixes too:
  ```bash
  ruff check --fix --unsafe-fixes .
  ```
