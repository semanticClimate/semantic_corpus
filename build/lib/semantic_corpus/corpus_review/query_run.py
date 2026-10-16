"""Query run record format for reproducible search/download iterations."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from semantic_corpus.core.exceptions import CorpusError


def load_pilot_config(config_path: Path) -> Dict[str, Any]:
    """Load a YAML pilot query configuration file."""
    config_path = Path(config_path)
    if not config_path.is_file():
        raise CorpusError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise CorpusError(f"Config must be a mapping: {config_path}")
    return data


def build_query_run_record(
    *,
    query_name: str,
    query_string: str,
    repository: str,
    limit: int,
    formats: List[str],
    output_dir: Path,
    result_count: int,
    downloaded_count: int = 0,
    notes: str = "",
    revision_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a query run record dict (ISO timestamp, system date of generation)."""
    return {
        "query_name": query_name,
        "query_string": query_string,
        "repository": repository,
        "limit": limit,
        "formats": formats,
        "output_dir": str(output_dir),
        "result_count": result_count,
        "downloaded_count": downloaded_count,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "revision_of": revision_of,
    }


def save_query_run_record(record: Dict[str, Any], output_dir: Path) -> Path:
    """Write query_run.json under output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir, "query_run.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
    return out_path


def load_query_run_record(path: Path) -> Dict[str, Any]:
    """Load query_run.json."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_query_run(record: Dict[str, Any]) -> str:
    """One-line summary for immediate reaction after a query run."""
    return (
        f"Query '{record.get('query_name')}': "
        f"{record.get('result_count')} results, "
        f"{record.get('downloaded_count', 0)} downloaded "
        f"-> {record.get('output_dir')}"
    )
