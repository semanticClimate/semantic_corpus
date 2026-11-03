"""Symbolic ``pipeline`` command: ``--query``/``--source`` → corpus → … → kg.

Orchestration uses **doit**; step actions are placeholders until wired to
``semantic_corpus.cluster_review``.
"""

from semantic_corpus.pipeline.config import (
    PipelineOptions,
    infer_from_mode,
)
from semantic_corpus.pipeline.steps import (
    FROM_MODES,
    STEP_DOCS,
    STEP_NAMES,
    all_deps,
    deps_for,
    doit_basename,
    graph_text,
    required_steps,
)

__all__ = [
    "FROM_MODES",
    "PipelineOptions",
    "STEP_DOCS",
    "STEP_NAMES",
    "all_deps",
    "deps_for",
    "doit_basename",
    "graph_text",
    "infer_from_mode",
    "required_steps",
]
