"""Symbolic pipeline steps and dependency graph (source of truth).

Design spine (docs/pipeline_kg_mappers.md §1.1):

  Collect → Corpus (+indexes) → Terms → Clusters [--kg] → Clean
       → Encyclopedia [--kg]

Two knowledge graphs (display artifacts, not doit steps):
  - after ``clusters``: incidence BKG without wiki annotations (``--kg``)
  - after ``encyclopedia``: same graph + Wikipedia payloads / optional Wikidata
    (``--kg``)

``clean`` curates using the clusters-stage graph (FP terms/packets) before
annotate effort.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Set

# How material enters: collect (--query / --source) or use an existing bag.
FROM_MODES = ("collect", "existing")

STEP_NAMES: List[str] = [
    "search",
    "collect",
    "corpus",
    "phrases",
    "pdfs",
    "clusters",
    "clean",
    "encyclopedia",
]

STEP_DOCS: Dict[str, str] = {
    "search": (
        "EPMC/other search only → query.json + search_results.json under --workdir"
    ),
    "collect": (
        "Fetch per-paper flat files under --workdir "
        "({id}.json/.xml/.pdf/.pdf.xml); --query remotes or resume existing hits"
    ),
    "corpus": (
        "Ensure corpus under --workdir and structural packet indexes "
        "on text components → packets/"
    ),
    "phrases": "Traverse indexed packet texts → extract terms → phrases/",
    "pdfs": "Fill missing valid PDFs into the corpus (parallel with phrases)",
    "clusters": (
        "Map: bipartite term↔packet BKG + communities → clusters/ "
        "(optional --kg: unannotated display graph)"
    ),
    "clean": (
        "Curate after clusters: remove FP packets/terms using BKG / islands "
        "(before encyclopedia)"
    ),
    "encyclopedia": (
        "Annotate retained terms with Wikipedia/Wikidata → encyclopedia/ "
        "(optional --kg: annotated display graph)"
    ),
}

# Steps that create the corpus artifact as part of their work.
MATERIAL_STEPS = frozenset({"search", "collect"})

_BASE_DEPS: Dict[str, List[str]] = {
    "search": [],
    "collect": ["search"],
    "corpus": [],  # filled by from_mode in deps_for
    "phrases": ["corpus"],
    "pdfs": ["corpus"],
    "clusters": ["phrases"],
    "clean": ["clusters"],
    "encyclopedia": ["clean"],
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


def deps_for(step: str, from_mode: str = "collect") -> List[str]:
    """Direct task dependencies under the inferred start mode."""
    if step not in _BASE_DEPS:
        raise KeyError(f"Unknown pipeline step: {step!r}")
    if from_mode not in FROM_MODES:
        raise ValueError(
            f"Unknown start mode {from_mode!r}; choose one of {FROM_MODES}"
        )
    if step == "search":
        if from_mode == "collect":
            return []
        # existing corpus: search is not required
        return []
    if step == "collect":
        if from_mode == "collect":
            return ["search"]
        return []
    if step == "corpus":
        if from_mode == "collect":
            return ["collect"]
        return []
    return list(_BASE_DEPS[step])


def all_deps(from_mode: str = "collect") -> Dict[str, List[str]]:
    return {name: deps_for(name, from_mode) for name in STEP_NAMES}


def doit_deps_for(step: str, from_mode: str = "collect") -> List[str]:
    return [doit_basename(d) for d in deps_for(step, from_mode)]


def required_steps(targets: Sequence[str], from_mode: str = "collect") -> List[str]:
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


def graph_text(from_mode: str = "collect") -> str:
    lines = [
        f"# pipeline graph (start={from_mode})",
        "# design: search → collect(paper:*) → corpus(+indexes) → terms → "
        "clusters[--kg] → clean → encyclopedia[--kg]",
        "",
    ]
    for name in STEP_NAMES:
        deps = deps_for(name, from_mode)
        if deps:
            lines.append(f"{' + '.join(deps)}  →  {name}")
        elif name == "corpus":
            lines.append("(existing --workdir)  →  corpus")
        elif name == "search" and from_mode != "collect":
            continue
        elif name == "collect" and from_mode != "collect":
            continue
        else:
            lines.append(f"{name}")
    lines.append("")
    lines.append("# flat workdir: {id}.json|.xml|.pdf|.pdf.xml (no downloads/ nesting)")
    lines.append("# collect options: --query (EPMC/remotes) | --source (static docs)")
    lines.append("# two KGs (flags, not steps): clusters --kg (plain); encyclopedia --kg (annotated)")
    lines.append("# clean curates after clusters; encyclopedia annotates retained terms")
    lines.append("# pdfs is parallel to the terms/map chain")
    return "\n".join(lines)
