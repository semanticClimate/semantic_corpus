"""Placeholder step actions: write stamp files under ``<workdir>/pipeline/``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from semantic_corpus.pipeline.config import options_from_env
from semantic_corpus.pipeline.steps import MATERIAL_STEPS


def pipeline_dir(workdir: Optional[Path] = None) -> Path:
    from semantic_corpus.pipeline.config import get_workdir

    root = workdir if workdir is not None else get_workdir()
    return root / "pipeline"


def stamp_path(step: str, workdir: Optional[Path] = None) -> Path:
    return pipeline_dir(workdir) / f"{step}.stamp"


def doit_db_path(workdir: Optional[Path] = None) -> Path:
    """Per-corpus doit dependency DB path (outside the BAGIT root).

    ``bagit.make_bag`` moves *all* top-level files under the corpus into
    ``data/``. Keeping ``.doit.db`` inside ``workdir`` therefore breaks Windows
    (and other) runs that create a fresh bag mid-pipeline: the DB files vanish
    before doit can dump them on exit.
    """
    import hashlib

    from semantic_corpus.pipeline.config import get_workdir
    from semantic_corpus.utils import get_project_temp_dir

    root = (workdir if workdir is not None else get_workdir()).resolve()
    digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:16]
    db_dir = get_project_temp_dir() / "pipeline_doit" / f"{root.name}_{digest}"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "doit.db"


def write_stamp(
    step: str, workdir: Path, extra: Optional[Dict[str, Any]] = None
) -> Path:
    path = stamp_path(step, workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    opts = options_from_env()
    payload: Dict[str, Any] = {
        "step": step,
        "status": "placeholder",
        "workdir": str(workdir),
        "written_at": datetime.now(timezone.utc).isoformat(),
        "options": opts.to_public_dict(),
        "note": f"Placeholder for pipeline step '{step}' — not yet wired to real work.",
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def run_placeholder(step: str) -> Dict[str, Any]:
    """Write a placeholder stamp for ``step`` and print a one-line status.

    ``query`` / ``documents`` also stamp ``corpus`` — they produce the BAGIT
    corpus at ``--workdir``.
    """
    from semantic_corpus.pipeline.config import get_workdir

    workdir = get_workdir()
    opts = options_from_env()
    path = write_stamp(step, workdir)

    extra = ""
    if step == "query" and opts.query:
        extra = f" query={opts.query!r} limit={opts.limit} repository={opts.repository!r}"
    elif step == "documents" and opts.source:
        extra = f" source={opts.source!r}"
    elif step == "phrases":
        extra = (
            f" method={opts.phrase_method} n={opts.phrase_n} top={opts.phrase_top}"
        )
    elif step == "clusters":
        extra = (
            f" algorithm={opts.cluster_algorithm} "
            f"resolution={opts.cluster_resolution}"
        )
    elif step == "encyclopedia":
        extra = (
            f" lang={opts.encyclopedia_lang} max_entries={opts.max_entries} "
            f"min_score={opts.min_score} min_paper_count={opts.min_paper_count} "
            f"from={opts.encyclopedia_source}"
        )
    elif step == "kg":
        extra = (
            f" links={opts.kg_links!r} max_island={opts.kg_max_island} "
            f"min_paper_count={opts.kg_min_paper_count} "
            f"max_terms={opts.kg_max_terms}"
        )

    print(f"[pipeline] {step}: placeholder → {path}{extra}")

    if step in MATERIAL_STEPS:
        cpath = write_stamp(
            "corpus",
            workdir,
            extra={"produced_by": step, "status": "placeholder"},
        )
        print(f"[pipeline] corpus: produced by {step} → {cpath}")

    return json.loads(path.read_text(encoding="utf-8"))


def stamp_exists(step: str, workdir: Optional[Path] = None) -> bool:
    return stamp_path(step, workdir).is_file()


def read_stamp(step: str, workdir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = stamp_path(step, workdir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
