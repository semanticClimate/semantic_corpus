"""doit task definitions for the symbolic ``pipeline`` steps.

Loaded via ``DoitMain(ModuleTaskLoader(...))`` from the ``pipeline`` CLI.
All actions are placeholders that write stamp files; wire real work later.

Environment (set by CLI before load):

- ``PIPELINE_WORKDIR`` / ``PIPELINE_FROM`` / ``PIPELINE_OPTIONS_JSON``
"""

from __future__ import annotations

from semantic_corpus.pipeline.actions import is_step_current, run_step
from semantic_corpus.pipeline.config import get_from_mode, get_workdir
from semantic_corpus.pipeline.placeholders import doit_db_path, stamp_path
from semantic_corpus.pipeline.steps import (
    STEP_DOCS,
    STEP_NAMES,
    doit_basename,
    doit_deps_for,
)

def _dep_file() -> str:
    path = doit_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


DOIT_CONFIG = {
    "dep_file": _dep_file(),
    "verbosity": 1,
}


def _uptodate(step: str):
    def _check(task=None, values=None):
        return is_step_current(step)

    return _check


def _task(step: str):
    from_mode = get_from_mode()
    return {
        "basename": doit_basename(step),
        "doc": STEP_DOCS.get(step, step),
        "actions": [(run_step, [step])],
        "targets": [str(stamp_path(step))],
        "task_dep": doit_deps_for(step, from_mode),
        "uptodate": [_uptodate(step)],
    }


def task_query():
    return _task("query")


def task_documents():
    return _task("documents")


def task_corpus():
    return _task("corpus")


def task_phrases():
    return _task("phrases")


def task_pdfs():
    return _task("pdfs")


def task_clusters():
    return _task("clusters")


def task_clean_fp():
    """Public step name is ``clean``; doit forbids basename ``clean``."""
    return _task("clean")


def task_encyclopedia():
    return _task("encyclopedia")


def task_kg():
    return _task("kg")


assert set(STEP_NAMES) == {
    "query",
    "documents",
    "corpus",
    "phrases",
    "pdfs",
    "clusters",
    "clean",
    "encyclopedia",
    "kg",
}

_ = get_workdir
