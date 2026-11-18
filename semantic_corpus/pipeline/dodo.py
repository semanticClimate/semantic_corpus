"""doit task definitions for the symbolic ``pipeline`` steps.

Loaded via ``DoitMain(ModuleTaskLoader(...))`` from the ``pipeline`` CLI.

Environment (set by CLI before load):

- ``PIPELINE_WORKDIR`` / ``PIPELINE_FROM`` / ``PIPELINE_OPTIONS_JSON``
"""

from __future__ import annotations

from semantic_corpus.pipeline.actions import is_step_current, run_paper, run_step
from semantic_corpus.pipeline.config import get_from_mode, get_workdir
from semantic_corpus.pipeline.doit_reporter import PipelineReporter
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
    # . = ran · -- = skipped; paper lines include [ok] / [xml=500] / [no_pmcid]
    "reporter": PipelineReporter,
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


def task_search():
    return _task("search")


def task_paper():
    """Dynamic per-PMC tasks with flat file targets (skip-if-exists)."""
    from semantic_corpus.pipeline.flat_corpus import (
        list_paper_ids_from_search,
        paper_done_enough,
        path_json,
        path_pdf,
        path_pdf_xml,
        path_search_results,
        path_xml,
    )

    workdir = get_workdir()
    results = path_search_results(workdir)
    if not results.is_file():
        # Until search runs, expose a no-op that waits on search.
        yield {
            "name": "await_search",
            "doc": "Placeholder until search_results.json exists",
            "actions": None,
            "task_dep": ["search"],
        }
        return

    for paper_id in list_paper_ids_from_search(workdir):
        targets = [
            str(path_json(workdir, paper_id)),
        ]
        # Best-effort optional targets — doit still runs if missing when action
        # writes them; uptodate uses paper_done_enough.
        optional = [
            path_xml(workdir, paper_id),
            path_pdf(workdir, paper_id),
            path_pdf_xml(workdir, paper_id),
        ]

        def _paper_uptodate(pid=paper_id, wd=workdir):
            def _check(task=None, values=None):
                return paper_done_enough(wd, pid)

            return _check

        yield {
            "name": paper_id,
            "doc": f"Fetch missing formats for {paper_id} (data/packets/)",
            "actions": [(run_paper, [paper_id])],
            "file_dep": [str(results)],
            "task_dep": ["search"],
            # Soft targets: action may skip (no PMCID) without writing XML
            "targets": targets,
            "uptodate": [_paper_uptodate()],
            # Do not abort the whole pipeline if one paper soft-fails mid-action;
            # run_paper itself catches RepositoryError. Keep continue on other errors.
            "meta": {"optional_targets": [str(p) for p in optional]},
        }


def task_collect():
    """Facade: depends on search + paper:* when hits are known."""
    from semantic_corpus.pipeline.flat_corpus import (
        list_paper_ids_from_search,
        path_search_results,
    )

    from_mode = get_from_mode()
    workdir = get_workdir()
    deps = list(doit_deps_for("collect", from_mode))
    results = path_search_results(workdir)
    if results.is_file():
        for paper_id in list_paper_ids_from_search(workdir):
            dep = f"paper:{paper_id}"
            if dep not in deps:
                deps.append(dep)
    spec = _task("collect")
    spec["task_dep"] = deps
    return spec


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


assert set(STEP_NAMES) == {
    "search",
    "collect",
    "corpus",
    "phrases",
    "pdfs",
    "clusters",
    "clean",
    "encyclopedia",
}

_ = get_workdir
