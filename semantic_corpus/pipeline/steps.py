"""Symbolic pipeline steps and dependency graph (source of truth).

``query`` / ``documents`` **produce** a BAGIT **corpus** under ``--workdir``.
``corpus`` is the gate later steps depend on (ensure / existing bag), not a
separate packaging product beyond what those material steps already write.

Step *actions* are placeholders until wired to cluster_review APIs.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Set

# How the corpus is obtained (inferred from --query / --source / neither).
FROM_MODES = ("query", "documents", "existing")

STEP_NAMES: List[str] = [
    "query",
    "documents",
    "corpus",
    "phrases",
    "pdfs",
    "clusters",
    "clean",
    "encyclopedia",
    "kg",
]

STEP_DOCS: Dict[str, str] = {
    "query": "Live search + download + package BAGIT corpus at --workdir",
    "documents": "Ingest --source files into BAGIT corpus at --workdir",
    "corpus": "Ensure corpus exists under --workdir (gate for later steps)",
    "phrases": "Keyphrase extract → phrases/ (method + params via flags)",
    "pdfs": "Fill missing valid PDFs into the corpus (parallel with phrases)",
    "clusters": "Bipartite KG (BKG) + communities → clusters/ (method flags)",
    "clean": "FP paper/term cleaning loop (recompute clusters)",
    "encyclopedia": (
        "Resolve retained phrases to Wikipedia/Wikidata "
        "(--encyclopedia-lang, --max-entries) → encyclopedia/"
    ),
    "kg": "Linked knowledge graph + islands (feedback to clean)",
}

# Steps that create the corpus artifact as part of their work.
MATERIAL_STEPS = frozenset({"query", "documents"})

_BASE_DEPS: Dict[str, List[str]] = {
    "query": [],
    "documents": [],
    "corpus": [],  # filled by from_mode in deps_for
    "phrases": ["corpus"],
    "pdfs": ["corpus"],
    "clusters": ["phrases"],
    "clean": ["clusters"],
    # Prefer clean decisions when present; graph only requires clusters so the
    # step is runnable before/without a clean session (see pipeline_encyclopedia.md).
    "encyclopedia": ["clusters"],
    # KG can run after clusters (BKG edges); wikipedia/wikidata soft-attach
    # encyclopedia nodes when entries.json exists.
    "kg": ["clusters"],
}

_DOIT_BASENAME: Dict[str, str] = {
    "clean": "clean_fp",
}


def doit_basename(step: str) -> str:
    if step not in _BASE_DEPS:
        raise KeyError(f"Unknown pipeline step: {step!r}")
    return _DOIT_BASENAME.get(step, step)


def public_step_from_doit(basename: str) -> str:
    for step, name in _DOIT_BASENAME.items():
        if name == basename:
            return step
    return basename


def deps_for(step: str, from_mode: str = "query") -> List[str]:
    """Direct task dependencies under the inferred start mode."""
    if step not in _BASE_DEPS:
        raise KeyError(f"Unknown pipeline step: {step!r}")
    if from_mode not in FROM_MODES:
        raise ValueError(
            f"Unknown start mode {from_mode!r}; choose one of {FROM_MODES}"
        )
    if step == "corpus":
        if from_mode == "query":
            return ["query"]
        if from_mode == "documents":
            return ["documents"]
        return []
    return list(_BASE_DEPS[step])


def all_deps(from_mode: str = "query") -> Dict[str, List[str]]:
    return {name: deps_for(name, from_mode) for name in STEP_NAMES}


def doit_deps_for(step: str, from_mode: str = "query") -> List[str]:
    return [doit_basename(d) for d in deps_for(step, from_mode)]


def required_steps(targets: Sequence[str], from_mode: str = "query") -> List[str]:
    unknown = [t for t in targets if t not in _BASE_DEPS]
    if unknown:
        raise KeyError(f"Unknown pipeline step(s): {unknown}")

    needed: Set[str] = set()

    def visit(name: str) -> None:
        if name in needed:
            return
        for dep in deps_for(name, from_mode):
            visit(dep)
        needed.add(name)

    for t in targets:
        visit(t)

    return [n for n in STEP_NAMES if n in needed]


def graph_text(from_mode: str = "query") -> str:
    lines = [f"# pipeline graph (start={from_mode})", ""]
    for name in STEP_NAMES:
        deps = deps_for(name, from_mode)
        if deps:
            lines.append(f"{' + '.join(deps)}  →  {name}")
        elif name == "corpus":
            lines.append(f"(existing --workdir)  →  corpus")
        else:
            lines.append(f"{name}")
    lines.append("")
    lines.append("# query/documents produce the corpus; phrases/pdfs need corpus")
    lines.append("# pdfs is parallel to phrases/clusters")
    return "\n".join(lines)
