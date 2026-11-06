"""Structural packet indexes under document containers (part of ``corpus``).

``corpus`` ensures text components are indexed. v1 writes a degenerate
manifest: one ``body`` packet per paper container. Does not depend on
matching/search. See docs/pipeline_kg_mappers.md §1.1 / §2.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.core.exceptions import CorpusError


def packets_dir(workdir: Path) -> Path:
    return Path(workdir) / "packets"


def packets_manifest_path(workdir: Path) -> Path:
    return packets_dir(workdir) / "manifest.json"


def build_packet_index(workdir: Path) -> Dict[str, Any]:
    """Index packets under paper containers (whole-paper body packet each)."""
    from semantic_corpus.cluster_review.step1 import (
        _paper_ids_from_metadata_dir,
        load_bagit_corpus,
        resolve_bagit_root,
    )

    workdir = Path(workdir)
    if not (workdir / "bagit.txt").is_file() and not (
        workdir / "data" / "bagit.txt"
    ).is_file():
        raise CorpusError(
            f"No BAGIT corpus at {workdir}; collect documents first"
        )

    summary = load_bagit_corpus(workdir, write_review_if_missing=False)
    bag_root = Path(summary.get("bag_root") or resolve_bagit_root(workdir))
    paper_ids: List[str] = list(summary.get("paper_ids") or [])
    if not paper_ids:
        meta = bag_root / "data" / "metadata"
        paper_ids = _paper_ids_from_metadata_dir(meta)

    containers: List[Dict[str, Any]] = []
    packets: List[Dict[str, Any]] = []
    for pid in sorted(paper_ids):
        cid = f"paper:{pid}"
        containers.append(
            {
                "id": cid,
                "kind": "paper",
                "paper_id": pid,
                "regions": {
                    "frontmatter": [],
                    "body": [f"packet:{pid}:body"],
                    "backmatter": [],
                },
            }
        )
        packets.append(
            {
                "id": f"packet:{pid}:body",
                "packet_type": "body",
                "label": pid.replace("europe_pmc_", ""),
                "parent_id": cid,
                "paper_id": pid,
                "storage": "in_container",
                "address": {
                    "scheme": "bagit_paper",
                    "paper_id": pid,
                    "note": "degenerate whole-paper body packet (v1)",
                },
            }
        )

    out_dir = packets_dir(workdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "step": "index",
        "workdir": str(workdir.resolve()),
        "params": {
            "mode": "degenerate_body_per_paper",
            "priority": ["source_numbers", "containment", "sequence"],
        },
        "counts": {
            "containers": len(containers),
            "packets": len(packets),
        },
        "containers": containers,
        "packets": packets,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path = packets_manifest_path(workdir)
    path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "step": "index",
        "manifest_path": str(path.resolve()),
        "counts": doc["counts"],
        "params": doc["params"],
        "written_at": doc["written_at"],
    }


def packet_index_is_current(workdir: Path) -> bool:
    path = packets_manifest_path(workdir)
    if not path.is_file():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(doc.get("packets"), list):
        return False
    bag = Path(workdir) / "bagit.txt"
    if bag.is_file() and bag.stat().st_mtime > path.stat().st_mtime:
        return False
    return True
