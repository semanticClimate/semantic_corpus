"""Tests for scripts/check_coding_style.py automatable rules."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coding_style.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_coding_style", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def checker():
    return _load_checker()


def test_fix_path_slash_simple(checker):
    src = 'root = Path(workdir) / "kg" / "graph.json"\n'
    out, n = checker.fix_path_slash(src)
    assert n == 1
    assert out == 'root = Path(workdir, "kg", "graph.json")\n'


def test_fix_status_literals(checker):
    src = (
        "from pathlib import Path\n\n"
        'n = sum(1 for row in rows if row.get("review_status") == "include")\n'
    )
    out, n = checker.fix_status_literals_in_source(src)
    assert n == 1
    assert "REVIEW_STATUS_INCLUDE" in out
    assert '== "include"' not in out
    assert "from semantic_corpus.corpus_review.constants import" in out


def test_check_path_slash_finding(checker, tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text('x = Path(workdir) / "data"\n', encoding="utf-8")
    findings = checker.check_path_slash(path, path.read_text(encoding="utf-8"))
    assert findings
    assert "prefer Path(a, b)" in findings[0]


def test_sys_path_exception_honoured(checker, tmp_path: Path):
    import ast

    src = (
        "import sys\n"
        "def add(p):\n"
        "    # style-exception: sys-path\n"
        "    sys.path.insert(0, p)\n"
    )
    path = tmp_path / "syspath.py"
    path.write_text(src, encoding="utf-8")
    tree = ast.parse(src)
    findings = checker.check_sys_path(path, tree, src.splitlines())
    assert findings == []


def test_status_literal_detection(checker, tmp_path: Path):
    import ast

    src = 'x = row.get("review_status") == "exclude"\n'
    path = tmp_path / "status.py"
    path.write_text(src, encoding="utf-8")
    findings = checker.check_status_literals(path, ast.parse(src))
    assert any("REVIEW_STATUS_EXCLUDE" in f for f in findings)


def test_git_diff_forbidden_helper_exists(checker):
    assert hasattr(checker, "check_git_diff_forbidden")
    assert "corpora/" in checker.FORBIDDEN_PREFIXES
