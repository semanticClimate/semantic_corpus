"""Runtime pipeline options (workdir, query/source, step parameters, …).

Flag groups (more will be added as steps are wired):

- **query** — always needs flags when used (``--query`` required; ``--limit``,
  ``--repository``, …)
- **documents** — ``--source``
- **corpus** — usually implied (produced by query/documents, or existing bag)
- **phrases** — method + params (``--phrase-method``, ``--phrase-n``, …)
- **clusters** — method + params (``--cluster-resolution``, …)
- **encyclopedia** / **kg** — ``--max-entries``, ``--kg-links``, ``--open``, …
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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
DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES = 100
DEFAULT_ENCYCLOPEDIA_MIN_SCORE = 0.0
DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT = 1
DEFAULT_ENCYCLOPEDIA_SOURCE = "auto"
DEFAULT_KG_MAX_ISLAND = 20
DEFAULT_KG_MAX_TERMS = 50
DEFAULT_KG_MIN_PAPER_COUNT = 2
DEFAULT_KG_LINKS = "clusters,wikipedia,wikidata"
KG_LINK_CHOICES: Tuple[str, ...] = ("clusters", "wikipedia", "wikidata")
ENCYCLOPEDIA_SOURCE_CHOICES: Tuple[str, ...] = ("auto", "clusters", "phrases")


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

    # --- encyclopedia / kg (stubs until wired) ---
    encyclopedia_lang: str = DEFAULT_ENCYCLOPEDIA_LANG
    max_entries: int = DEFAULT_ENCYCLOPEDIA_MAX_ENTRIES
    min_score: float = DEFAULT_ENCYCLOPEDIA_MIN_SCORE
    min_paper_count: int = DEFAULT_ENCYCLOPEDIA_MIN_PAPER_COUNT
    encyclopedia_source: str = DEFAULT_ENCYCLOPEDIA_SOURCE
    kg_max_island: int = DEFAULT_KG_MAX_ISLAND
    kg_max_terms: int = DEFAULT_KG_MAX_TERMS
    kg_min_paper_count: int = DEFAULT_KG_MIN_PAPER_COUNT
    kg_links: str = DEFAULT_KG_LINKS

    def __post_init__(self) -> None:
        if self.from_mode not in FROM_MODES:
            raise ValueError(f"from_mode must be one of {FROM_MODES}")
        if self.query and self.source:
            raise ValueError("Use either --query or --source, not both")
        if self.max_entries < 1:
            raise ValueError("--max-entries must be >= 1")
        if self.min_paper_count < 1:
            raise ValueError("--min-paper-count must be >= 1")
        if self.kg_max_terms < 1:
            raise ValueError("--kg-max-terms must be >= 1")
        if self.kg_min_paper_count < 1:
            raise ValueError("--kg-min-paper-count must be >= 1")
        if self.encyclopedia_source not in ENCYCLOPEDIA_SOURCE_CHOICES:
            raise ValueError(
                f"--encyclopedia-from must be one of {ENCYCLOPEDIA_SOURCE_CHOICES}"
            )
        unknown = [
            p for p in self.kg_link_list() if p not in KG_LINK_CHOICES
        ]
        if unknown:
            raise ValueError(
                f"Unknown --kg-links token(s) {unknown}; "
                f"choose from {list(KG_LINK_CHOICES)}"
            )

    def kg_link_list(self) -> Tuple[str, ...]:
        parts = [p.strip() for p in (self.kg_links or "").split(",")]
        return tuple(p for p in parts if p)

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
