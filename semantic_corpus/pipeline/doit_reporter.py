"""Custom doit reporter: legend + per-paper outcome suffixes.

Doit defaults::

    .  task   → ran this time
    -- task   → skipped (already up to date)

For ``paper:{id}`` we append a short status (``ok``, ``no_pmcid``, ``xml=500``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from doit.reporter import ConsoleReporter


def status_label_from_streams(streams: Any) -> str:
    """Compact label from download ``streams`` notes."""
    notes = [str(x) for x in (streams or [])]
    joined = " ".join(notes)
    for note in notes:
        if note.startswith("xml-http:"):
            return f"xml={note.split(':', 1)[1]}"
        if note.startswith("pdf-http:"):
            return f"pdf={note.split(':', 1)[1]}"
    if "no_pmcid" in notes or "no_pmcid" in joined:
        return "no_pmcid"
    if "xml" in notes or "xml-from-pdf" in notes or "skip-xml" in notes:
        if any(n.startswith("pdf-http:") for n in notes):
            pdf = next(n for n in notes if n.startswith("pdf-http:"))
            return f"ok,pdf={pdf.split(':', 1)[1]}"
        return "ok"
    if "unavailable" in notes:
        return "unavailable"
    if "error" in notes:
        return "error"
    if notes:
        return notes[-1][:24]
    return ""


def status_label_from_disk(workdir, paper_id: str) -> str:
    """Status for an up-to-date paper from packets on disk."""
    from semantic_corpus.pipeline.flat_corpus import (
        find_best_xml,
        load_paper_json,
        paper_stem,
    )

    stem = paper_stem(paper_id)
    if find_best_xml(workdir, stem) is not None:
        return "ok"
    meta = load_paper_json(workdir, stem) or {}
    recorded = str(meta.get("_collect_xml") or "").strip().lower()
    if recorded:
        return recorded
    http = meta.get("_collect_xml_http")
    if http is not None and str(http).strip():
        return f"xml={http}"
    return "cached"


def status_label_for_result(result: Optional[Dict[str, Any]], workdir, paper_id: str) -> str:
    if isinstance(result, dict):
        explicit = str(result.get("status_label") or "").strip()
        if explicit:
            return explicit
        from_streams = status_label_from_streams(result.get("streams"))
        if from_streams:
            return from_streams
        if result.get("success") and (
            result.get("xml") or "ok" in str(result.get("streams") or "")
        ):
            return "ok"
        err = str(result.get("error") or "")
        if "No PMCID" in err or "pmcid" in err.lower():
            return "no_pmcid"
        code = result.get("status_code")
        if code:
            return f"xml={code}"
    return status_label_from_disk(workdir, paper_id)


def _paper_id_from_task_name(name: str) -> Optional[str]:
    if name.startswith("paper:"):
        return name.split(":", 1)[1]
    return None


class PipelineReporter(ConsoleReporter):
    """Console reporter with deferred paper lines + status suffixes."""

    desc = "pipeline console ( . ran / -- skipped + paper status )"

    def initialize(self, tasks, selected_tasks):
        self.write(
            "[pipeline] marks: . = ran this time · -- = skipped (already done)\n"
        )

    def execute_task(self, task):
        # Defer paper lines until success/failure so we can show HTTP status.
        if _paper_id_from_task_name(task.name):
            return
        super().execute_task(task)

    def add_success(self, task):
        pid = _paper_id_from_task_name(task.name)
        if not pid:
            return
        if not task.actions or task.name[0] == "_":
            return
        label = self._label_for_paper(task, pid)
        suffix = f"  [{label}]" if label else ""
        self.write(f".  {task.title()}{suffix}\n")

    def add_failure(self, task, fail):
        pid = _paper_id_from_task_name(task.name)
        if pid and task.actions and task.name[0] != "_":
            self.write(f"!! {task.title()}  [fail]\n")
        super().add_failure(task, fail)

    def skip_uptodate(self, task):
        if task.name[0] == "_":
            return
        pid = _paper_id_from_task_name(task.name)
        if not pid:
            self.write(f"-- {task.title()}\n")
            return
        label = self._label_for_paper(task, pid, from_disk=True)
        suffix = f"  [{label}]" if label else ""
        self.write(f"-- {task.title()}{suffix}\n")

    def _label_for_paper(self, task, paper_id: str, *, from_disk: bool = False) -> str:
        from semantic_corpus.pipeline.config import get_workdir

        workdir = get_workdir()
        result = None
        if not from_disk:
            result = getattr(task, "result", None)
            if not isinstance(result, dict):
                values = getattr(task, "values", None)
                if isinstance(values, dict) and values:
                    result = values
        return status_label_for_result(result, workdir, paper_id)
