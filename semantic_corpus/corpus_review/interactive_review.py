"""Interactive Y/N review session for corpus selection."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import (
    REVIEW_STATUS_EXCLUDE,
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
)
from semantic_corpus.corpus_review.review_schema import validate_review_row
from semantic_corpus.corpus_review.review_table import export_review_tables
from semantic_corpus.corpus_review.text_preview import build_paper_preview, strip_markup


@dataclass
class ReviewSessionConfig:
    """Configuration for an interactive review session."""

    review_table_path: Path
    query_dir: Optional[Path] = None
    xml_dir: Optional[Path] = None
    corpus_dir: Optional[Path] = None
    search_results_path: Optional[Path] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    status_filter: str = REVIEW_STATUS_REVIEW
    topic_filter: Optional[str] = None
    redo: bool = False
    intro_max_chars: int = 800


@dataclass
class ReviewDecision:
    """One reviewer decision."""

    paper_id: str
    previous_status: str
    new_status: str
    previous_notes: str
    new_notes: str


@dataclass
class ReviewSession:
    """In-memory interactive review session."""

    config: ReviewSessionConfig
    rows: List[Dict[str, Any]] = field(default_factory=list)
    queue_indices: List[int] = field(default_factory=list)
    position: int = 0
    undo_stack: List[ReviewDecision] = field(default_factory=list)
    search_index: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, config: ReviewSessionConfig) -> "ReviewSession":
        path = Path(config.review_table_path)
        if not path.is_file():
            raise CorpusError(f"Review table not found: {path}")
        with open(path, "r", encoding="utf-8") as handle:
            rows = json.load(handle)
        if not isinstance(rows, list):
            raise CorpusError("Review table JSON must contain a list of rows")

        session = cls(config=config, rows=rows)
        session._load_search_index()
        session.queue_indices = session._build_queue()
        return session

    def _load_search_index(self) -> None:
        search_path = self.config.search_results_path
        if not search_path and self.config.query_dir:
            candidate = Path(self.config.query_dir, "search_results.json")
            if candidate.is_file():
                search_path = candidate
        if not search_path or not Path(search_path).is_file():
            return

        with open(search_path, "r", encoding="utf-8") as handle:
            results = json.load(handle)
        if not isinstance(results, list):
            return

        for paper in results:
            for key in ("pmcid", "pmid", "doi", "paper_id", "openalex_id", "pid"):
                value = paper.get(key)
                if value:
                    self.search_index[str(value)] = paper

    def _lookup_search_metadata(self, row: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("pmcid", "pmid", "doi", "paper_id"):
            value = row.get(key)
            if value and str(value) in self.search_index:
                return self.search_index[str(value)]
        paper_id = row.get("paper_id") or ""
        short_id = paper_id.replace("europe_pmc_", "")
        return self.search_index.get(short_id, {})

    def _topic_matches(self, row: Dict[str, Any], topic: str) -> bool:
        topic = topic.lower()
        haystack = " ".join(
            str(row.get(column) or "")
            for column in (
                "location_terms",
                "pollutant_terms",
                "health_terms",
                "cluster_terms",
                "encyclopedia_category",
                "title",
                "abstract_snippet",
            )
        ).lower()
        return topic in haystack

    def _build_queue(self) -> List[int]:
        indices: List[int] = []
        for index, row in enumerate(self.rows):
            status = row.get("review_status", REVIEW_STATUS_REVIEW)
            if not self.config.redo and status in (
                REVIEW_STATUS_INCLUDE,
                REVIEW_STATUS_EXCLUDE,
            ):
                continue
            if (
                self.config.status_filter != "all"
                and status != self.config.status_filter
            ):
                continue

            score = int(row.get("score") or 0)
            if self.config.min_score is not None and score < self.config.min_score:
                continue
            if self.config.max_score is not None and score > self.config.max_score:
                continue
            if self.config.topic_filter and not self._topic_matches(
                row, self.config.topic_filter
            ):
                continue
            indices.append(index)

        indices.sort(
            key=lambda idx: (
                -int(self.rows[idx].get("score") or 0),
                self.rows[idx].get("title") or "",
            )
        )
        return indices

    @property
    def total(self) -> int:
        return len(self.queue_indices)

    @property
    def completed(self) -> int:
        return self.position

    @property
    def finished(self) -> bool:
        return self.position >= len(self.queue_indices)

    def current_row(self) -> Optional[Dict[str, Any]]:
        if self.finished:
            return None
        return self.rows[self.queue_indices[self.position]]

    def current_preview(self) -> Dict[str, str]:
        row = self.current_row()
        if row is None:
            return {}
        return build_paper_preview(
            row,
            search_metadata=self._lookup_search_metadata(row),
            query_dir=self.config.query_dir,
            xml_dir=self.config.xml_dir,
            corpus_dir=self.config.corpus_dir,
            intro_max_chars=self.config.intro_max_chars,
        )

    def format_current_paper(self) -> str:
        row = self.current_row()
        if row is None:
            return "Review complete."

        preview = self.current_preview()
        lines = [
            "",
            f"[{self.position + 1}/{self.total}]  score={row.get('score')}  status={row.get('review_status')}",
            f"paper_id: {row.get('paper_id')}",
        ]
        if row.get("pmcid"):
            lines.append(f"pmcid: {row.get('pmcid')}")
        if row.get("doi"):
            lines.append(f"doi: {row.get('doi')}")
        if preview.get("topics"):
            lines.append(f"topics: {preview['topics']}")
        if row.get("cluster_id") is not None:
            lines.append(
                f"cluster: {row.get('cluster_id')} ({row.get('cluster_terms') or ''})"
            )
        if row.get("encyclopedia_category"):
            lines.append(
                "encyclopedia: "
                f"{row.get('encyclopedia_category')} "
                f"(score={row.get('encyclopedia_score')})"
            )

        lines.extend(
            [
                "",
                f"Title: {strip_markup(row.get('title') or '')}",
                f"Authors: {row.get('authors') or ''}",
                f"Journal: {row.get('journal') or ''}  Date: {row.get('publication_date') or ''}",
                f"Full text: xml={row.get('has_xml')} pdf={row.get('has_pdf')}",
            ]
        )

        if preview.get("abstract"):
            lines.extend(["", "Abstract:", preview["abstract"]])
        if preview.get("intro"):
            lines.extend(["", "Introduction excerpt:", preview["intro"]])
        elif preview.get("xml_path"):
            lines.append("")
            lines.append("(No introduction excerpt extracted from XML.)")
        if row.get("review_notes"):
            lines.extend(["", f"Notes: {row.get('review_notes')}"])

        lines.extend(
            [
                "",
                "Decision: [Y] include  [N] exclude  [S] skip  [U] undo  [Q] quit save",
            ]
        )
        return "\n".join(lines)

    def apply_decision(
        self,
        choice: str,
        notes: str = "",
    ) -> Tuple[bool, str]:
        """Apply one Y/N/S/U/Q decision to the current paper."""
        choice = choice.strip().lower()
        if choice in {"q", "quit"}:
            self.save()
            return False, "Saved review table. Goodbye."

        if choice in {"u", "undo"}:
            if not self.undo_stack:
                return True, "Nothing to undo."
            decision = self.undo_stack.pop()
            row = self._row_by_paper_id(decision.paper_id)
            row["review_status"] = decision.previous_status
            row["review_notes"] = decision.previous_notes
            if self.position > 0:
                self.position -= 1
            self.save()
            return True, f"Undid decision for {decision.paper_id}."

        row = self.current_row()
        if row is None:
            self.save()
            return False, "Review complete."

        if choice in {"y", "yes", "include"}:
            new_status = REVIEW_STATUS_INCLUDE
        elif choice in {"n", "no", "exclude"}:
            new_status = REVIEW_STATUS_EXCLUDE
        elif choice in {"s", "skip"}:
            new_status = REVIEW_STATUS_REVIEW
        else:
            return True, "Unknown choice. Use Y/N/S/U/Q."

        decision = ReviewDecision(
            paper_id=row["paper_id"],
            previous_status=row.get("review_status", REVIEW_STATUS_REVIEW),
            new_status=new_status,
            previous_notes=row.get("review_notes") or "",
            new_notes=notes,
        )
        row["review_status"] = new_status
        if notes:
            row["review_notes"] = notes
        validate_review_row(row)
        self.undo_stack.append(decision)
        self.position += 1
        self.save()
        return True, f"Marked {row['paper_id']} as {new_status}."

    def _row_by_paper_id(self, paper_id: str) -> Dict[str, Any]:
        for row in self.rows:
            if row.get("paper_id") == paper_id:
                return row
        raise CorpusError(f"Paper not found in review table: {paper_id}")

    def save(self) -> Dict[str, Path]:
        """Write updated review tables next to the source JSON."""
        output_dir = Path(self.config.review_table_path).parent
        return export_review_tables(self.rows, output_dir)

    def summary(self) -> Dict[str, int]:
        counts = {
            REVIEW_STATUS_INCLUDE: 0,
            REVIEW_STATUS_REVIEW: 0,
            REVIEW_STATUS_EXCLUDE: 0,
        }
        for row in self.rows:
            status = row.get("review_status", REVIEW_STATUS_REVIEW)
            counts[status] = counts.get(status, 0) + 1
        return counts


def run_interactive_review(config: ReviewSessionConfig) -> Dict[str, int]:
    """Run an interactive terminal review loop."""
    session = ReviewSession.load(config)
    if session.total == 0:
        raise CorpusError("No papers match the current review filters.")

    print(f"Loaded {len(session.rows)} rows; {session.total} papers in queue.")
    print(session.format_current_paper())

    while not session.finished:
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            session.save()
            break

        if not choice:
            continue

        note = ""
        if choice.lower() in {"y", "yes", "n", "no", "include", "exclude"}:
            note = input("Optional note (Enter to skip): ").strip()

        continue_session, message = session.apply_decision(choice, notes=note)
        print(message)
        if not continue_session:
            break
        if not session.finished:
            print(session.format_current_paper())

    summary = session.summary()
    print(
        "Summary: "
        f"include={summary.get(REVIEW_STATUS_INCLUDE, 0)}, "
        f"review={summary.get(REVIEW_STATUS_REVIEW, 0)}, "
        f"exclude={summary.get(REVIEW_STATUS_EXCLUDE, 0)}"
    )
    return summary
