#!/usr/bin/env python3
"""Automatable coding-style checks for semantic_corpus (docs/coding_style.md).

Checks (AST / text):
  - Path constructed with ``/`` instead of comma args
  - ``sys.path`` mutation (unless ``# style-exception: sys-path`` on prior line)
  - review status string literals outside constants.py
  - large inline HTML/CSS/JS string constants
  - functions longer than ``--max-function-lines`` (unless
    ``# style-exception: long-function`` on the def line or the line above)

Usage:
  ./venv/bin/python scripts/check_coding_style.py
  ./venv/bin/python scripts/check_coding_style.py --fix-path
  ./venv/bin/python scripts/check_coding_style.py --git-diff HEAD~1
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple  # Tuple used in fix return types

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "semantic_corpus"

STATUS_LITERALS = frozenset({"include", "exclude", "review"})
STATUS_CONST = {
    "include": "REVIEW_STATUS_INCLUDE",
    "exclude": "REVIEW_STATUS_EXCLUDE",
    "review": "REVIEW_STATUS_REVIEW",
}
MARKUP_RE = re.compile(r"<(style|script|html|!DOCTYPE)\b", re.I)
PATH_CHAIN_RE = re.compile(
    r"Path\((?P<args>[^()\n]+)\)(?P<chain>(?:\s*/\s*(?:\"[^\"]+\"|'[^']+'))+)"
)
EXCEPTION_SYS = re.compile(r"style-exception:\s*sys-path")
EXCEPTION_LONG = re.compile(r"style-exception:\s*long-function")
FORBIDDEN_PREFIXES = ("corpora/", "temp/")


def _iter_py_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _prior_line_has_exception(lines: Sequence[str], lineno: int, pattern: re.Pattern) -> bool:
    # lineno is 1-based
    for idx in (lineno - 1, lineno - 2):
        if 0 <= idx < len(lines) and pattern.search(lines[idx]):
            return True
    return False


def check_sys_path(path: Path, tree: ast.AST, lines: Sequence[str]) -> List[str]:
    findings: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # sys.path.insert / append / extend
        if isinstance(func, ast.Attribute) and func.attr in {"insert", "append", "extend"}:
            val = func.value
            if isinstance(val, ast.Attribute) and val.attr == "path":
                if isinstance(val.value, ast.Name) and val.value.id == "sys":
                    if _prior_line_has_exception(lines, node.lineno, EXCEPTION_SYS):
                        continue
                    findings.append(
                        f"{path}:{node.lineno}: sys.path mutation "
                        f"(add `# style-exception: sys-path` if deliberate)"
                    )
    return findings


def check_status_literals(path: Path, tree: ast.AST) -> List[str]:
    if path.name == "constants.py" and path.parent.name == "corpus_review":
        return []
    findings: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if (
                    isinstance(comparator, ast.Constant)
                    and isinstance(comparator.value, str)
                    and comparator.value in STATUS_LITERALS
                ):
                    # Only flag when left side looks like review_status access
                    left = node.left
                    interesting = False
                    if isinstance(left, ast.Constant) and left.value == "review_status":
                        interesting = True
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute):
                        if left.func.attr == "get" and left.args:
                            arg0 = left.args[0]
                            if (
                                isinstance(arg0, ast.Constant)
                                and arg0.value == "review_status"
                            ):
                                interesting = True
                    if isinstance(left, ast.Subscript):
                        sl = left.slice
                        if isinstance(sl, ast.Constant) and sl.value == "review_status":
                            interesting = True
                    if interesting:
                        findings.append(
                            f"{path}:{node.lineno}: use {STATUS_CONST[comparator.value]} "
                            f"instead of {comparator.value!r}"
                        )
    return findings


def check_long_functions(
    path: Path, tree: ast.AST, lines: Sequence[str], max_lines: int
) -> List[str]:
    findings: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", None) or node.lineno
        n = end - node.lineno + 1
        if n <= max_lines:
            continue
        if _prior_line_has_exception(lines, node.lineno, EXCEPTION_LONG):
            continue
        # also accept exception in docstring first line
        doc = ast.get_docstring(node) or ""
        if "style-exception: long-function" in doc:
            continue
        findings.append(
            f"{path}:{node.lineno}: function {node.name!r} is {n} lines "
            f"(max {max_lines}; mark `# style-exception: long-function` if kept)"
        )
    return findings


def check_inline_markup(path: Path, tree: ast.AST, min_chars: int) -> List[str]:
    findings: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value
        if len(text) < min_chars:
            continue
        if MARKUP_RE.search(text):
            findings.append(
                f"{path}:{node.lineno}: large inline HTML/CSS/JS string "
                f"({len(text)} chars) — prefer external .html/.css/.js"
            )
    return findings


def check_path_slash(path: Path, source: str) -> List[str]:
    findings: List[str] = []
    for match in PATH_CHAIN_RE.finditer(source):
        # skip if line has style-exception
        line_start = source.rfind("\n", 0, match.start()) + 1
        line_no = source.count("\n", 0, match.start()) + 1
        line = source[line_start : source.find("\n", match.start())]
        if "style-exception: path-slash" in line:
            continue
        findings.append(
            f"{path}:{line_no}: prefer Path(a, b) over Path(a) / b "
            f"(found Path(...){match.group('chain').strip()})"
        )
    return findings


def fix_path_slash(source: str) -> Tuple[str, int]:
    """Rewrite simple ``Path(args) / "a" / "b"`` chains to comma form."""

    def repl(match: re.Match) -> str:
        args = match.group("args").strip()
        chain = match.group("chain")
        extras = re.findall(r"\"[^\"]+\"|'[^']+'", chain)
        if not extras:
            return match.group(0)
        return f"Path({args}, {', '.join(extras)})"

    new_source, n = PATH_CHAIN_RE.subn(repl, source)
    return new_source, n


def fix_status_literals_in_source(source: str) -> Tuple[str, int]:
    """Replace review_status == \"include\" style compares with constants."""
    count = 0
    patterns = [
        (
            re.compile(
                r'(\.get\(\s*["\']review_status["\']\s*\)\s*==\s*)["\']include["\']'
            ),
            r"\1REVIEW_STATUS_INCLUDE",
        ),
        (
            re.compile(
                r'(\.get\(\s*["\']review_status["\']\s*\)\s*==\s*)["\']exclude["\']'
            ),
            r"\1REVIEW_STATUS_EXCLUDE",
        ),
        (
            re.compile(
                r'(\.get\(\s*["\']review_status["\']\s*\)\s*==\s*)["\']review["\']'
            ),
            r"\1REVIEW_STATUS_REVIEW",
        ),
        (
            re.compile(
                r'(\[\s*["\']review_status["\']\s*\]\s*==\s*)["\']include["\']'
            ),
            r"\1REVIEW_STATUS_INCLUDE",
        ),
        (
            re.compile(
                r'(\[\s*["\']review_status["\']\s*\]\s*==\s*)["\']exclude["\']'
            ),
            r"\1REVIEW_STATUS_EXCLUDE",
        ),
        (
            re.compile(
                r'(\[\s*["\']review_status["\']\s*\]\s*==\s*)["\']review["\']'
            ),
            r"\1REVIEW_STATUS_REVIEW",
        ),
    ]
    out = source
    for cre, repl in patterns:
        out, n = cre.subn(repl, out)
        count += n
    if count and "REVIEW_STATUS_INCLUDE" in out:
        # Ensure import if missing
        if "REVIEW_STATUS_INCLUDE" in out and "REVIEW_STATUS_INCLUDE" not in source:
            pass
        need = [
            name
            for name in (
                "REVIEW_STATUS_INCLUDE",
                "REVIEW_STATUS_EXCLUDE",
                "REVIEW_STATUS_REVIEW",
            )
            if name in out
        ]
        import_line = (
            "from semantic_corpus.corpus_review.constants import (\n    "
            + ",\n    ".join(sorted(set(need)))
            + ",\n)\n"
        )
        if "from semantic_corpus.corpus_review.constants import" not in out:
            # insert after last leading import block
            lines = out.splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_at = i + 1
                elif line.strip() == "" and insert_at:
                    continue
                elif insert_at and not (
                    line.startswith("import ") or line.startswith("from ")
                ):
                    break
            lines.insert(insert_at, import_line)
            out = "".join(lines)
        else:
            # extend existing import if needed — leave for manual if complex
            pass
    return out, count


def check_git_diff_forbidden(base: str) -> List[str]:
    findings: List[str] = []
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", base],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return [f"git diff failed: {exc}"]
    for line in proc.stdout.splitlines():
        path = line.strip()
        if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            findings.append(
                f"git-diff: new file under forbidden prefix: {path} "
                f"(keep corpora/temp off product commits)"
            )
    return findings


def analyze_file(
    path: Path,
    *,
    max_function_lines: int,
    markup_min_chars: int,
    check_long: bool,
    check_markup: bool,
) -> List[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    findings: List[str] = []
    findings.extend(check_path_slash(path, source))
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: syntax error: {exc}"]
    findings.extend(check_sys_path(path, tree, lines))
    findings.extend(check_status_literals(path, tree))
    if check_markup:
        findings.extend(check_inline_markup(path, tree, markup_min_chars))
    if check_long:
        findings.extend(check_long_functions(path, tree, lines, max_function_lines))
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=PACKAGE,
        help="Package root to scan (default: semantic_corpus/)",
    )
    parser.add_argument(
        "--max-function-lines",
        type=int,
        default=80,
        help="Max function length before finding (default 80)",
    )
    parser.add_argument(
        "--markup-min-chars",
        type=int,
        default=400,
        help="Min chars for inline markup finding (default 400)",
    )
    parser.add_argument(
        "--check-long-functions",
        action="store_true",
        help="Emit findings for long functions (off by default until baseline marked)",
    )
    parser.add_argument(
        "--check-markup",
        action="store_true",
        help="Emit findings for large inline HTML/CSS/JS strings (manual extract)",
    )
    parser.add_argument(
        "--fix-path",
        action="store_true",
        help="Rewrite simple Path(a) / 'b' chains to Path(a, 'b')",
    )
    parser.add_argument(
        "--fix-status",
        action="store_true",
        help="Rewrite review_status == 'include'|… to REVIEW_STATUS_* constants",
    )
    parser.add_argument(
        "--git-diff",
        metavar="BASE",
        help="Also flag newly added corpora/ or temp/ files since BASE",
    )
    parser.add_argument(
        "--baseline-long",
        type=Path,
        help="Optional file listing path:lineno:name entries treated as known long funcs",
    )
    args = parser.parse_args(argv)

    root: Path = args.root
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    fixed_files = 0
    if args.fix_path or args.fix_status:
        for path in _iter_py_files(root):
            original = path.read_text(encoding="utf-8")
            updated = original
            total = 0
            if args.fix_path:
                updated, n = fix_path_slash(updated)
                total += n
            if args.fix_status and not (
                path.name == "constants.py" and path.parent.name == "corpus_review"
            ):
                updated, n = fix_status_literals_in_source(updated)
                total += n
            if total and updated != original:
                path.write_text(updated, encoding="utf-8")
                fixed_files += 1
                print(f"fixed {path} ({total} substitutions)")
        print(f"autofix complete: {fixed_files} files changed")

    findings: List[str] = []
    for path in _iter_py_files(root):
        findings.extend(
            analyze_file(
                path,
                max_function_lines=args.max_function_lines,
                markup_min_chars=args.markup_min_chars,
                check_long=args.check_long_functions,
                check_markup=args.check_markup,
            )
        )

    if args.git_diff:
        findings.extend(check_git_diff_forbidden(args.git_diff))

    for item in findings:
        print(item)

    if findings:
        print(f"\n{len(findings)} coding-style finding(s)", file=sys.stderr)
        return 1
    print("coding-style checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
