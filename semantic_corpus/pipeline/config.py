"""Runtime pipeline options (workdir, query/source, step parameters, …).

Flag groups (more will be added as steps are wired):

- **query** — always needs flags when used (``--query`` required; ``--limit``,
  ``--repository``, …)
- **documents** — ``--source``
- **corpus** — usually implied (produced by query/documents, or existing bag)
- **phrases** — method + params (``--phrase-method``, ``--phrase-n``, …)
- **clusters** — method + params (``--cluster-resolution``, …)
- **encyclopedia** / **kg** — optional parameters (stubs for now)
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from semantic_corpus.pipeline.steps import FROM_MODES

ENV_WORKDIR = "PIPELINE_WORKDIR"
ENV_FROM = "PIPELINE_FROM"
ENV_OPTIONS_JSON = "PIPELINE_OPTIONS_JSON"
ENV_PLACEHOLDER = "PIPELINE_PLACEHOLDER"

DEFAULT_WORKDIR = "temp/pipeline_demo"
DEFAULT_FROM = "existing"
DEFAULT_LIMIT = 50
DEFAULT_REPOSITORY = "europe_pmc"
DEFAULT_PHRASE_METHOD = "tfidf"
DEFAULT_PHRASE_N = 3
DEFAULT_PHRASE_TOP = 15
DEFAULT_CLUSTER_RESOLUTION = 1.0
DEFAULT_CLUSTER_ALGORITHM = "louvain"
DEFAULT_ENCYCLOPEDIA_LANG = "en"
DEFAULT_KG_MAX_ISLAND = 20


@dataclass(frozen=True)
class PipelineOptions:
    """CLI / env snapshot passed into doit tasks."""

    workdir: Path
    from_mode: str  # query | documents | existing

    # --- query (required flags when start=query) ---
    query: Optional[str] = None
    limit: Optional[int] = None
    repository: Optional[str] = None

    # --- documents ---
    source: Optional[str] = None

    # --- phrases ---
    phrase_method: str = DEFAULT_PHRASE_METHOD
    phrase_n: int = DEFAULT_PHRASE_N
    phrase_top: int = DEFAULT_PHRASE_TOP

    # --- clusters ---
    cluster_resolution: float = DEFAULT_CLUSTER_RESOLUTION
    cluster_algorithm: str = DEFAULT_CLUSTER_ALGORITHM

    # --- encyclopedia / kg (stubs) ---
    encyclopedia_lang: str = DEFAULT_ENCYCLOPEDIA_LANG
    kg_max_island: int = DEFAULT_KG_MAX_ISLAND

    def __post_init__(self) -> None:
        if self.from_mode not in FROM_MODES:
            raise ValueError(f"from_mode must be one of {FROM_MODES}")
        if self.query and self.source:
            raise ValueError("Use either --query or --source, not both")

    def to_public_dict(self) -> Dict[str, Any]:
        """JSON-serialisable view for stamps / debugging."""
        d = asdict(self)
        d["workdir"] = str(self.workdir)
        return d


def infer_from_mode(query: Optional[str], source: Optional[str]) -> str:
    if query and source:
        raise ValueError("Use either --query or --source, not both")
    if query:
        return "query"
    if source:
        return "documents"
    return "existing"


def apply_env(opts: PipelineOptions) -> None:
    """Publish options for doit tasks (reloaded dodo reads these)."""
    os.environ[ENV_WORKDIR] = str(opts.workdir.resolve())
    os.environ[ENV_FROM] = opts.from_mode
    os.environ[ENV_OPTIONS_JSON] = json.dumps(opts.to_public_dict())


def get_workdir() -> Path:
    return Path(os.environ.get(ENV_WORKDIR, DEFAULT_WORKDIR)).expanduser().resolve()


def get_from_mode() -> str:
    return os.environ.get(ENV_FROM, DEFAULT_FROM)


def options_from_env() -> PipelineOptions:
    raw = os.environ.get(ENV_OPTIONS_JSON)
    if not raw:
        return PipelineOptions(workdir=get_workdir(), from_mode=get_from_mode())
    data = json.loads(raw)
    data["workdir"] = Path(data["workdir"])
    return PipelineOptions(**data)


def get_query() -> Optional[str]:
    return options_from_env().query


def get_source() -> Optional[str]:
    return options_from_env().source


def get_limit() -> Optional[int]:
    return options_from_env().limit
