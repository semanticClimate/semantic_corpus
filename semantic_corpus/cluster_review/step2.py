"""Step 2: phrase extraction with disk cache.

Default method: corpus TF-IDF on **XML body only** (no front matter, no references).
YAKE remains available as ``method="yake"`` (same text policy).

Stop / noise word lists are editable text files under
``semantic_corpus/cluster_review/lists/`` (see ``lists/README.md``).
"""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from semantic_corpus.cluster_review.lists_loader import (
    acronym_skip,
    common_titlecase,
    figure_table_noise,
    latex_noise,
    phrase_boilerplate,
    proper_boilerplate,
    scientific_discourse,
)
from semantic_corpus.cluster_review.step1 import load_bagit_corpus
from semantic_corpus.core.exceptions import CorpusError

DEFAULT_LAN = "en"
DEFAULT_N = 3
DEFAULT_TOP = 15
DEFAULT_MAX_BODY_CHARS = 50_000
DEFAULT_METHOD = "tfidf"
DEFAULT_SCORE_DIGITS = 4
VALID_METHODS = frozenset({"tfidf", "yake"})

# Loaded from ``cluster_review/lists/*.txt`` (editable; see lists/README.md).
# Back-compat alias for callers that import BOILERPLATE_PHRASES.
BOILERPLATE_PHRASES = phrase_boilerplate()

ProgressCallback = Callable[[int, int, str, float], None]


def normalize_phrase(phrase: str) -> str:
    """Lowercase and collapse whitespace."""
    return " ".join(str(phrase).lower().split())


def _display_rank(form: str) -> Tuple[int, int, int, int]:
    """Higher is better for choosing a surface capitalization."""
    if not form:
        return (0, 0, 0, 0)
    letters = [c for c in form if c.isalpha()]
    n_upper = sum(1 for c in letters if c.isupper())
    n_lower = sum(1 for c in letters if c.islower())
    has_upper = 1 if n_upper else 0
    # Prefer true acronyms (ISM) and camelCase (NegE) over Title case / lower
    is_acronym = 1 if letters and n_lower == 0 and 2 <= len(letters) <= 6 else 0
    is_camel = 1 if n_upper >= 2 and n_lower >= 1 else 0
    is_title = 0
    if " " in form:
        words = form.split()
        if words and all(w[:1].isupper() for w in words if w):
            is_title = 1
    elif letters and form[0].isupper() and n_upper == 1:
        is_title = 1
    return (has_upper, is_acronym, is_camel, is_title)


def prefer_phrase_display(
    current: Optional[str], candidate: Optional[str]
) -> str:
    """Pick the better capitalization between two surface forms."""
    cur = " ".join(str(current or "").split())
    cand = " ".join(str(candidate or "").split())
    if not cand:
        return cur
    if not cur:
        return cand
    if normalize_phrase(cur) != normalize_phrase(cand):
        return cur
    if _display_rank(cand) > _display_rank(cur):
        return cand
    return cur


def select_phrase_display(phrase: str, text: str) -> str:
    """Recover usual capitalization of ``phrase`` from ``text`` when possible.

    ``phrase`` is the lowercase key; the return value is a surface form such as
    ``ISM``, ``NegE``, or ``Indian Ocean``. Falls back to ``phrase`` when the
    document has no cased match.
    """
    norm = normalize_phrase(phrase)
    if not norm:
        return ""
    if not text:
        return norm
    parts = norm.split()
    pattern = re.compile(
        r"\b" + r"\s+".join(re.escape(p) for p in parts) + r"\b",
        re.IGNORECASE,
    )
    best = norm
    for match in pattern.finditer(text):
        surface = " ".join(match.group(0).split())
        best = prefer_phrase_display(best, surface)
    return best


def attach_phrase_displays(
    phrases: Sequence[Dict[str, Any]],
    text: str,
) -> List[Dict[str, Any]]:
    """Ensure each phrase dict has a ``display`` capitalization hint."""
    out: List[Dict[str, Any]] = []
    for item in phrases or []:
        phrase = normalize_phrase(item.get("phrase") or "")
        if not phrase:
            continue
        existing = item.get("display")
        recovered = select_phrase_display(phrase, text)
        display = prefer_phrase_display(
            prefer_phrase_display(phrase, existing if isinstance(existing, str) else None),
            recovered,
        )
        row = dict(item)
        row["phrase"] = phrase
        row["display"] = display or phrase
        out.append(row)
    return out


def round_score(score: float, ndigits: int = DEFAULT_SCORE_DIGITS) -> float:
    """Round phrase scores for compact JSON/CSV (default 4 decimal places)."""
    try:
        return round(float(score), ndigits)
    except (TypeError, ValueError):
        return 0.0


def paper_text_from_metadata(metadata: Dict[str, Any]) -> str:
    """Build input text from title + abstract (abstract-only OK if no title)."""
    title = str(metadata.get("title") or "").strip()
    abstract = str(
        metadata.get("abstract")
        or metadata.get("abstracttext")
        or metadata.get("abstractText")
        or ""
    ).strip()
    if title and abstract:
        return f"{title}\n\n{abstract}"
    return title or abstract


def find_paper_xml(bag_root: Path, paper_id: str) -> Optional[Path]:
    """Locate full-text XML for a paper under BAGIT documents/."""
    from semantic_corpus.repositories._ids import paper_id_stems

    bag_root = Path(bag_root)
    stems = paper_id_stems(paper_id)
    dirs = [
        Path(bag_root, "data", "documents", "xml"),
        Path(bag_root, "data", "data", "documents", "xml"),
        Path(bag_root, "documents", "xml"),
        Path(bag_root, "documents"),
    ]
    for directory in dirs:
        if not directory.is_dir():
            continue
        for stem in stems:
            path = Path(directory, f"{stem}.xml")
            if path.is_file() and path.stat().st_size > 0:
                return path
    return None


# Body section titles (normalized) skipped when indexing — not content.
_SKIP_BODY_SECTION_TITLES = frozenset(
    {
        "references",
        "reference",
        "bibliography",
        "literature cited",
        "works cited",
        "acknowledgments",
        "acknowledgements",
        "acknowledgment",
        "acknowledgement",
        "funding",
        "author contributions",
        "competing interests",
        "conflict of interest",
        "conflicts of interest",
        "data availability",
        "supplementary material",
        "supplementary materials",
        "supporting information",
        "appendix",
        "appendices",
    }
)


def _local_tag(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return str(tag)


def _section_title_text(sec) -> str:
    title_el = sec.find("./{*}title")
    if title_el is None:
        title_el = sec.find("{*}title")
    if title_el is None:
        return ""
    return " ".join("".join(title_el.itertext()).split()).lower()


def _paragraph_in_skipped_context(p) -> bool:
    """True if paragraph sits under refs / acknowledgments / similar."""
    skip_tags = {
        "ref-list",
        "ref",
        "mixed-citation",
        "element-citation",
        "citation-alternatives",
        "fn-group",
        "footnote",
        "ack",
        "bio",
        "author-notes",
        "front",
        "back",
    }
    for ancestor in p.iterancestors():
        tag = _local_tag(ancestor.tag)
        if tag in skip_tags:
            return True
        if tag == "sec":
            title = _section_title_text(ancestor)
            if title in _SKIP_BODY_SECTION_TITLES or any(
                title.startswith(t + " ") for t in _SKIP_BODY_SECTION_TITLES
            ):
                return True
    return False


def extract_plain_text_from_xml(
    xml_path: Path,
    *,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
    max_paragraphs: int = 200,
) -> Dict[str, str]:
    """Pull title/abstract (for optional use) and indexable body from JATS/PMC XML.

    Body text excludes front matter, ``<back>``, ref-lists, and sections titled
    References / Bibliography / Acknowledgments / etc.
    """
    from lxml import etree

    xml_path = Path(xml_path)
    out = {"title": "", "abstract": "", "body": ""}
    if not xml_path.is_file():
        return out
    try:
        root = etree.parse(str(xml_path)).getroot()
    except etree.XMLSyntaxError:
        return out

    def _el_text(element) -> str:
        return " ".join("".join(element.itertext()).split())

    title_el = root.find(".//{*}article-title")
    if title_el is not None:
        out["title"] = _el_text(title_el)

    abstract_parts: List[str] = []
    for abstract in root.findall(".//{*}abstract"):
        atype = (abstract.get("abstract-type") or "").lower()
        if atype in ("teaser", "graphical"):
            continue
        for p in abstract.findall(".//{*}p"):
            t = _el_text(p)
            if t:
                abstract_parts.append(t)
        if not abstract_parts:
            t = _el_text(abstract)
            if t:
                abstract_parts.append(t)
        if abstract_parts:
            break
    out["abstract"] = "\n".join(abstract_parts)

    body_parts: List[str] = []
    chars = 0
    # Prefer paragraphs under <body> only; never walk <front> / <back>
    body = root.find(".//{*}body")
    paragraphs = (
        body.findall(".//{*}p") if body is not None else root.findall(".//{*}body//{*}p")
    )
    for p in paragraphs:
        if _paragraph_in_skipped_context(p):
            continue
        t = _el_text(p)
        if not t:
            continue
        body_parts.append(t)
        chars += len(t) + 1
        if len(body_parts) >= max_paragraphs or chars >= max_body_chars:
            break
    body_text = "\n".join(body_parts)
    if len(body_text) > max_body_chars:
        body_text = body_text[:max_body_chars]
    out["body"] = body_text
    return out


def build_phrase_input_text(
    metadata: Dict[str, Any],
    *,
    bag_root: Optional[Path] = None,
    paper_id: str = "",
    include_xml_body: bool = True,
    include_front_matter: bool = False,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
) -> Dict[str, Any]:
    """Assemble phrase text for indexing.

    Default: **XML body only** (no title/abstract/front matter, no references).
    Set ``include_front_matter=True`` to also use metadata title+abstract.

    Returns dict with ``text``, ``meta_text``, ``body_text``, ``text_source``, ``xml_path``.
    """
    meta_text = ""
    sources: List[str] = []
    if include_front_matter:
        meta_text = paper_text_from_metadata(metadata)
        if meta_text:
            sources.append("title+abstract")

    xml_path: Optional[Path] = None
    xml_body = ""
    if include_xml_body and bag_root is not None and paper_id:
        xml_path = find_paper_xml(bag_root, paper_id)
        if xml_path is not None:
            xml_bits = extract_plain_text_from_xml(
                xml_path, max_body_chars=max_body_chars
            )
            if include_front_matter and not meta_text and (
                xml_bits.get("title") or xml_bits.get("abstract")
            ):
                meta_text = "\n\n".join(
                    p for p in (xml_bits.get("title"), xml_bits.get("abstract")) if p
                )
                if meta_text and "title+abstract" not in sources:
                    sources.append("xml-front")
            xml_body = xml_bits.get("body") or ""
            if xml_body:
                sources.append("xml-body")

    # Default indexing text is body-only; front matter is optional add-on
    if include_front_matter:
        chunks = [c for c in (meta_text, xml_body) if c]
    else:
        chunks = [c for c in (xml_body,) if c]
    text = "\n\n".join(chunks)
    return {
        "text": text,
        "meta_text": meta_text if include_front_matter else "",
        "body_text": xml_body,
        "text_source": "+".join(sources) if sources else "empty",
        "xml_path": str(xml_path.resolve()) if xml_path else "",
    }


# Back-compat alias
build_yake_input_text = build_phrase_input_text


def phrases_dir_for_corpus(corpus_dir: Path) -> Path:
    """Cache directory beside the corpus: ``<corpus_dir>/phrases/``."""
    return Path(corpus_dir, "phrases")


def phrase_cache_path(phrases_dir: Path, paper_id: str) -> Path:
    safe = str(paper_id).replace("/", "_")
    return Path(phrases_dir, f"{safe}.json")


def clear_all_caches(
    corpus_dir: Path,
    *,
    remove_dir: bool = True,
) -> Dict[str, Any]:
    """Delete all phrase cache files for a corpus (clean slate for retesting)."""
    corpus_dir = Path(corpus_dir)
    phrases_dir = phrases_dir_for_corpus(corpus_dir)
    deleted: List[str] = []
    errors: List[str] = []

    if phrases_dir.is_dir():
        for path in sorted(
            list(phrases_dir.glob("*.json")) + list(phrases_dir.glob("*.csv"))
        ):
            try:
                path.unlink()
                deleted.append(str(path.resolve()))
            except OSError as exc:
                errors.append(f"{path}: {exc}")
        if remove_dir:
            try:
                remaining = list(phrases_dir.iterdir())
                if not remaining:
                    phrases_dir.rmdir()
            except OSError as exc:
                errors.append(f"{phrases_dir}: {exc}")
    elif phrases_dir.exists():
        raise CorpusError(f"phrases path exists but is not a directory: {phrases_dir}")

    return {
        "step": 2,
        "action": "clear_all_caches",
        "corpus_dir": str(corpus_dir.resolve()),
        "phrases_dir": str(phrases_dir.resolve()),
        "deleted_count": len(deleted),
        "deleted": deleted,
        "errors": errors,
        "cleared": len(errors) == 0,
    }


def _filter_phrases(
    raw: Sequence[tuple],
    *,
    top: int,
) -> List[Dict[str, Any]]:
    """Normalize (phrase, score) tuples; drop boilerplate; keep best ``top``."""
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not item or len(item) < 2:
            continue
        phrase, score = item[0], item[1]
        norm = normalize_phrase(phrase)
        if (
            not norm
            or norm in seen
            or norm in phrase_boilerplate()
            or norm in scientific_discourse()
        ):
            continue
        if len(norm) < 2:
            continue
        seen.add(norm)
        surface = " ".join(str(phrase).split())
        out.append(
            {
                "phrase": norm,
                "display": prefer_phrase_display(norm, surface),
                "score": round_score(score),
            }
        )
        if len(out) >= top:
            break
    return out


def extract_phrases_from_text(
    text: str,
    *,
    lan: str = DEFAULT_LAN,
    n: int = DEFAULT_N,
    top: int = DEFAULT_TOP,
    extractor: Any = None,
) -> List[Dict[str, Any]]:
    """Run YAKE on ``text``; return ``[{phrase, score}, ...]`` (lower scores = better)."""
    text = (text or "").strip()
    if not text:
        return []
    if extractor is None:
        extractor = _make_yake_extractor(lan=lan, n=n, top=top)
    raw = extractor.extract_keywords(text)
    return _filter_phrases(raw or [], top=top)


def _load_metadata(metadata_dir: Path, paper_id: str) -> Dict[str, Any]:
    path = Path(metadata_dir, f"{paper_id}_metadata.json")
    if not path.is_file():
        raise CorpusError(f"Missing metadata for {paper_id}: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_cached_phrases(path: Path) -> Optional[Dict[str, Any]]:
    """Load one paper's phrase JSON if present and valid."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "phrases" not in data:
        return None
    return data


def save_paper_phrases(
    path: Path,
    *,
    paper_id: str,
    phrases: List[Dict[str, Any]],
    text_source: str,
    params: Dict[str, Any],
    elapsed_s: float,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "paper_id": paper_id,
        "phrases": phrases,
        "phrase_count": len(phrases),
        "text_source": text_source,
        "params": params,
        "elapsed_s": round(float(elapsed_s), 4),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def write_phrases_csv(
    phrases_dir: Path,
    papers: Sequence[Dict[str, Any]],
) -> Path:
    """Write long-form ``phrases.csv``: one row per (paper, phrase)."""
    path = Path(phrases_dir, "phrases.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["paper_id", "rank", "phrase", "display", "score", "source"],
        )
        writer.writeheader()
        for paper in papers:
            paper_id = paper.get("paper_id") or ""
            source = paper.get("source") or ""
            for rank, item in enumerate(paper.get("phrases") or [], start=1):
                phrase = item.get("phrase") or ""
                writer.writerow(
                    {
                        "paper_id": paper_id,
                        "rank": rank,
                        "phrase": phrase,
                        "display": item.get("display") or phrase,
                        "score": round_score(item.get("score"))
                        if item.get("score") is not None
                        else "",
                        "source": source,
                    }
                )
    return path


def write_phrases_summary_csv(
    phrases_dir: Path,
    papers: Sequence[Dict[str, Any]],
    *,
    top_n: int = 5,
    score_higher_is_better: bool = False,
) -> Tuple[Path, Path]:
    """Write inspection CSVs beside the phrase cache.

    Returns:
        ``(phrases_summary.csv, phrases_terms.csv)``
    """
    phrases_dir = Path(phrases_dir)
    phrases_dir.mkdir(parents=True, exist_ok=True)

    summary_path = Path(phrases_dir, "phrases_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "paper_id",
                "phrase_count",
                "top_phrases",
                "text_source",
                "source",
            ],
        )
        writer.writeheader()
        for paper in papers:
            phrases = paper.get("phrases") or []
            top = "; ".join(
                str(p.get("display") or p.get("phrase") or "")
                for p in phrases[:top_n]
                if p.get("phrase")
            )
            writer.writerow(
                {
                    "paper_id": paper.get("paper_id") or "",
                    "phrase_count": len(phrases),
                    "top_phrases": top,
                    "text_source": paper.get("text_source") or "",
                    "source": paper.get("source") or "",
                }
            )

    term_stats: Dict[str, Dict[str, Any]] = {}
    for paper in papers:
        paper_id = str(paper.get("paper_id") or "")
        for item in paper.get("phrases") or []:
            phrase = str(item.get("phrase") or "").strip()
            if not phrase:
                continue
            score = item.get("score")
            try:
                score_f = round_score(score) if score is not None else None
            except (TypeError, ValueError):
                score_f = None
            display = prefer_phrase_display(
                phrase,
                item.get("display") if isinstance(item.get("display"), str) else None,
            )
            entry = term_stats.get(phrase)
            if entry is None:
                term_stats[phrase] = {
                    "phrase": phrase,
                    "display": display,
                    "n_papers": 1,
                    "best_score": score_f,
                    "paper_ids": [paper_id] if paper_id else [],
                }
            else:
                entry["display"] = prefer_phrase_display(entry.get("display"), display)
                if paper_id and paper_id not in entry["paper_ids"]:
                    entry["n_papers"] += 1
                    entry["paper_ids"].append(paper_id)
                if score_f is not None:
                    if entry["best_score"] is None:
                        entry["best_score"] = score_f
                    elif score_higher_is_better and score_f > entry["best_score"]:
                        entry["best_score"] = score_f
                    elif not score_higher_is_better and score_f < entry["best_score"]:
                        entry["best_score"] = score_f

    terms_path = Path(phrases_dir, "phrases_terms.csv")
    with open(terms_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["phrase", "display", "n_papers", "best_score", "paper_ids"],
        )
        writer.writeheader()

        def _term_sort_key(r: Dict[str, Any]):
            score = r["best_score"]
            if score is None:
                score_key = (True, 0.0)
            elif score_higher_is_better:
                score_key = (False, -float(score))
            else:
                score_key = (False, float(score))
            return (-int(r["n_papers"]),) + score_key + (r["phrase"],)

        rows = sorted(term_stats.values(), key=_term_sort_key)
        for row in rows:
            writer.writerow(
                {
                    "phrase": row["phrase"],
                    "display": row.get("display") or row["phrase"],
                    "n_papers": row["n_papers"],
                    "best_score": row["best_score"],
                    "paper_ids": ";".join(row["paper_ids"]),
                }
            )

    return summary_path, terms_path


def find_phrase_cache(
    corpus_dir: Path,
    paper_ids: Sequence[str],
) -> Dict[str, Any]:
    """Summarize which papers already have phrase cache files."""
    phrases_dir = phrases_dir_for_corpus(corpus_dir)
    cached: List[str] = []
    missing: List[str] = []
    for paper_id in paper_ids:
        path = phrase_cache_path(phrases_dir, paper_id)
        if load_cached_phrases(path) is not None:
            cached.append(paper_id)
        else:
            missing.append(paper_id)
    return {
        "phrases_dir": str(phrases_dir.resolve()) if phrases_dir.exists() else str(phrases_dir),
        "cached_count": len(cached),
        "missing_count": len(missing),
        "cached_ids": cached,
        "missing_ids": missing,
        "ready": len(missing) == 0 and len(paper_ids) > 0,
    }


def _make_yake_extractor(*, lan: str, n: int, top: int) -> Any:
    """Create a YAKE KeywordExtractor, or raise CorpusError if yake is missing."""
    try:
        import yake
    except ImportError as exc:
        import sys

        raise CorpusError(
            "yake is required for method='yake'. Install into this interpreter:\n"
            f"  {sys.executable} -m pip install yake\n"
            "or: pip install 'semantic_corpus[cluster_review]'\n"
            f"(current python: {sys.executable})"
        ) from exc
    return yake.KeywordExtractor(lan=lan, n=n, top=max(top * 2, top))


def _require_sklearn() -> Any:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as exc:
        import sys

        raise CorpusError(
            "scikit-learn is required for method='tfidf'. Install:\n"
            f"  {sys.executable} -m pip install scikit-learn\n"
            "or: pip install 'semantic_corpus[cluster_review]'\n"
            f"(current python: {sys.executable})"
        ) from exc
    return TfidfVectorizer



def _preprocess_phrase_text(text: str) -> str:
    """Strip light LaTeX / markup noise before vectorizing."""
    if not text:
        return ""
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = re.sub(r"[{}\[\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def proper_phrases_from_text(
    text: str,
    *,
    min_count: int = 2,
    top: int = 8,
) -> List[Dict[str, Any]]:
    """Extract capitalized phrases from document text.

    Document-grounded (not query seeds): multiword proper phrases are kept on
    first sight; single tokens need ``min_count`` repeats. Surfaces geography
    like ``Indian Ocean`` that TF-IDF buries under method jargon.
    """
    if not text:
        return []
    # Multiword Proper Phrases (allow small connectors)
    pattern = re.compile(
        r"\b([A-Z][a-z]+(?:\s+(?:of|and|the|in|on|for)?\s*[A-Z][a-z]+)+)\b"
    )
    multi_counts: Dict[str, int] = {}
    multi_display: Dict[str, str] = {}
    for match in pattern.finditer(text):
        raw = " ".join(match.group(1).split())
        raw = re.sub(r"^(?:Of|And|The|In|On|For)\s+", "", raw)
        if len(raw.split()) < 2:
            continue
        norm = normalize_phrase(raw)
        if (
            not norm
            or norm in phrase_boilerplate()
            or norm in scientific_discourse()
        ):
            continue
        multi_counts[norm] = multi_counts.get(norm, 0) + 1
        multi_display[norm] = prefer_phrase_display(multi_display.get(norm), raw)

    skip_acro = acronym_skip()
    title_skip = (
        common_titlecase() | phrase_boilerplate() | scientific_discourse()
    )

    # Acronyms — always counted unless listed in acronym_skip.txt
    single_counts: Dict[str, int] = {}
    single_display: Dict[str, str] = {}
    for match in re.finditer(r"\b([A-Z]{2,6})\b", text):
        tok = match.group(1)
        if tok in skip_acro:
            continue
        norm = normalize_phrase(tok)
        if not norm or norm in title_skip:
            continue
        single_counts[norm] = single_counts.get(norm, 0) + 1
        single_display[norm] = prefer_phrase_display(single_display.get(norm), tok)

    # Titlecase tokens not at sentence start (reduces "While"/"These" noise)
    for match in re.finditer(
        r"(?<=[a-z0-9,;:])\s+([A-Z][a-z]{2,})\b", text
    ):
        tok = match.group(1)
        norm = normalize_phrase(tok)
        if not norm or norm in title_skip:
            continue
        single_counts[norm] = single_counts.get(norm, 0) + 1
        single_display[norm] = prefer_phrase_display(single_display.get(norm), tok)

    # CamelCase / mixed acronyms (NegE, ZeroE, IsMR-style tokens)
    for match in re.finditer(r"\b([A-Z][a-zA-Z]*[A-Z][a-zA-Z]*)\b", text):
        tok = match.group(1)
        if tok in skip_acro:
            continue
        norm = normalize_phrase(tok)
        if not norm or norm in title_skip or len(norm) < 2:
            continue
        single_counts[norm] = single_counts.get(norm, 0) + 1
        single_display[norm] = prefer_phrase_display(single_display.get(norm), tok)

    multis_ranked: List[Dict[str, Any]] = []
    for phrase, count in multi_counts.items():
        phrase = re.sub(r"^the\s+", "", phrase)
        if len(phrase.split()) < 2:
            continue
        display = multi_display.get(phrase) or phrase
        display = re.sub(r"^(?:The|Of|And)\s+", "", display)
        multis_ranked.append(
            {
                "phrase": phrase,
                "display": display,
                "score": round_score(float(count) * 10.0),
            }
        )
    singles_ranked: List[Dict[str, Any]] = []
    for phrase, count in single_counts.items():
        if count >= min_count:
            singles_ranked.append(
                {
                    "phrase": phrase,
                    "display": single_display.get(phrase) or phrase,
                    "score": round_score(float(count)),
                }
            )
    multis_ranked.sort(key=lambda r: (-r["score"], -len(r["phrase"]), r["phrase"]))
    singles_ranked.sort(key=lambda r: (-r["score"], r["phrase"]))
    # Keep both channels so frequent place names are not buried by multiwords
    return multis_ranked[:top] + singles_ranked[:top]


def merge_tfidf_and_proper(
    tfidf_phrases: Sequence[Dict[str, Any]],
    proper_phrases: Sequence[Dict[str, Any]],
    *,
    top: int = DEFAULT_TOP,
    max_proper: int = 10,
) -> List[Dict[str, Any]]:
    """Reserve slots for proper phrases, fill the rest from TF-IDF."""
    proper_cap = max(0, min(max_proper, max(top - 5, 5) if top >= 8 else top // 2))
    cleaned: List[Dict[str, Any]] = []
    for item in proper_phrases or []:
        phrase = normalize_phrase(item.get("phrase") or "")
        if (
            not phrase
            or phrase in proper_boilerplate()
            or phrase in phrase_boilerplate()
            or phrase in scientific_discourse()
        ):
            continue
        try:
            raw = float(item.get("score") or 0.0)
        except (TypeError, ValueError):
            raw = 0.0
        display = prefer_phrase_display(
            phrase,
            item.get("display") if isinstance(item.get("display"), str) else None,
        )
        cleaned.append(
            {
                "phrase": phrase,
                "display": display,
                "score": round_score(1.0 + raw * 0.01),
            }
        )

    multis = [p for p in cleaned if " " in p["phrase"]]
    singles = [p for p in cleaned if " " not in p["phrase"]]
    multis.sort(key=lambda r: (-r["score"], -len(r["phrase"]), r["phrase"]))
    singles.sort(key=lambda r: (-r["score"], r["phrase"]))
    single_slots = min(5, max(2, proper_cap // 3), len(singles))
    multi_slots = max(0, proper_cap - single_slots)
    proper_part = multis[:multi_slots] + singles[:single_slots]

    used = {p["phrase"] for p in proper_part}
    rest = [
        p
        for p in tfidf_phrases
        if normalize_phrase(p.get("phrase") or "") not in used
    ]
    combined = proper_part + rest
    return combined[:top]


def tfidf_phrases_for_corpus(
    texts: Sequence[str],
    *,
    n: int = DEFAULT_N,
    top: int = DEFAULT_TOP,
    max_df: float = 1.0,
    min_df: int = 1,
    tf_blend: float = 0.55,
) -> List[List[Dict[str, Any]]]:
    """Fit corpus-aware n-gram weights and return top phrases per document.

    Blends normalized local TF with TF-IDF so theme terms that appear often in a
    paper (but also across a focused corpus) still surface for bipartite edges.
    ``tf_blend`` is the weight on local TF (rest on TF-IDF). Higher score = better.
    """
    import numpy as np

    TfidfVectorizer = _require_sklearn()
    cleaned = [_preprocess_phrase_text(t or "") for t in texts]
    if not any(cleaned):
        return [[] for _ in cleaned]

    n_docs = len(cleaned)
    effective_max_df: Any = max_df
    if n_docs < 3:
        effective_max_df = 1.0

    shared_kwargs = dict(
        ngram_range=(1, max(1, n)),
        lowercase=True,
        stop_words="english",
        min_df=min(min_df, n_docs),
        max_df=effective_max_df,
        token_pattern=r"(?u)\b[a-z][a-z0-9\-]{1,}\b",
        sublinear_tf=True,
        norm="l2",
    )
    tfidf_vec = TfidfVectorizer(use_idf=True, smooth_idf=True, **shared_kwargs)
    tf_vec = TfidfVectorizer(use_idf=False, **shared_kwargs)
    try:
        tfidf_matrix = tfidf_vec.fit_transform(cleaned)
        # Same vocab: transform with a TF vectorizer fitted on the same docs
        tf_matrix = tf_vec.fit_transform(cleaned)
    except ValueError:
        return [[] for _ in cleaned]

    # Align feature spaces (should match with identical kwargs + docs)
    tfidf_names = list(tfidf_vec.get_feature_names_out())
    tf_names = list(tf_vec.get_feature_names_out())
    if tfidf_names != tf_names:
        # Fall back to TF-IDF only if vocab diverges
        tf_matrix = tfidf_matrix
        tf_blend = 0.0

    feature_names = tfidf_names
    blend = max(0.0, min(1.0, float(tf_blend)))
    results: List[List[Dict[str, Any]]] = []
    for row_idx in range(tfidf_matrix.shape[0]):
        tfidf_row = tfidf_matrix.getrow(row_idx).toarray().ravel()
        tf_row = tf_matrix.getrow(row_idx).toarray().ravel()
        scores = blend * tf_row + (1.0 - blend) * tfidf_row
        if not np.any(scores > 0):
            results.append([])
            continue
        # Candidate pool: union of top raw TF and TF-IDF indices
        pool_k = max(top * 4, 40)
        cand = set(scores.argsort()[::-1][:pool_k].tolist())
        cand.update(tfidf_row.argsort()[::-1][:pool_k].tolist())
        cand.update(tf_row.argsort()[::-1][:pool_k].tolist())
        ranked = sorted(cand, key=lambda i: float(scores[i]), reverse=True)
        seen: set[str] = set()
        phrases: List[Dict[str, Any]] = []
        for idx in ranked:
            weight = float(scores[idx])
            if weight <= 0:
                break
            phrase = normalize_phrase(feature_names[int(idx)])
            if (
                not phrase
                or phrase in seen
                or phrase in phrase_boilerplate()
                or phrase in scientific_discourse()
                or phrase in latex_noise()
                or len(phrase) < 2
            ):
                continue
            latex = latex_noise()
            if any(tok in latex for tok in phrase.split()):
                continue
            if re.fullmatch(r"[0-9\-]+", phrase):
                continue
            if re.fullmatch(r"[a-z]{0,3}\d+[a-z0-9\-]*", phrase):
                continue
            if phrase in figure_table_noise():
                continue
            # Drop n-grams that are pure discourse furniture (e.g. "see figure")
            if all(
                tok in scientific_discourse() or tok in figure_table_noise()
                for tok in phrase.split()
            ):
                continue
            seen.add(phrase)
            phrases.append({"phrase": phrase, "score": round_score(weight)})
            if len(phrases) >= top:
                break
        results.append(phrases)
    return results


def _cache_matches_params(record: Dict[str, Any], params: Dict[str, Any]) -> bool:
    cached = record.get("params") or {}
    for key in (
        "method",
        "n",
        "top",
        "text_fields",
        "include_front_matter",
        "phrase_schema",
    ):
        if cached.get(key) != params.get(key):
            return False
    return True


def _resolve_paper_selection(
    bag_summary: Dict[str, Any],
    paper_ids: Optional[Sequence[str]],
    corpus_dir: Path,
) -> Tuple[Path, Path, List[str]]:
    bag_root = Path(bag_summary["bag_root"])
    metadata_dir = Path(bag_summary["metadata_dir"])
    all_ids = list(bag_summary.get("paper_ids") or [])
    if paper_ids is not None:
        wanted = set(paper_ids)
        selected = [pid for pid in all_ids if pid in wanted]
        unknown = wanted - set(all_ids)
        if unknown:
            raise CorpusError(
                f"Unknown paper_id(s) for this corpus: {', '.join(sorted(unknown))}"
            )
    else:
        selected = all_ids
    if not selected:
        raise CorpusError(f"No papers found in corpus: {corpus_dir}")
    return bag_root, metadata_dir, selected


def extract_phrases(
    corpus_dir: Path,
    *,
    method: str = DEFAULT_METHOD,
    lan: str = DEFAULT_LAN,
    n: int = DEFAULT_N,
    top: int = DEFAULT_TOP,
    use_cache: bool = True,
    force: bool = False,
    paper_ids: Optional[Sequence[str]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    extractor: Any = None,
    include_xml_body: bool = True,
    include_front_matter: bool = False,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
) -> Dict[str, Any]:
    """Extract phrases for all papers in a BAGIT corpus (Step 2).

    Default ``method="tfidf"``: one corpus-wide TF-IDF fit on **XML body only**
    (no front matter, no references). ``method="yake"`` uses the same text.

    Caches under ``<corpus_dir>/phrases/`` with the same JSON/CSV contract as before.
    """
    corpus_dir = Path(corpus_dir)
    method = (method or DEFAULT_METHOD).strip().lower()
    if method not in VALID_METHODS:
        raise CorpusError(
            f"Unknown phrase method {method!r}; expected one of {sorted(VALID_METHODS)}"
        )
    if n < 1:
        raise CorpusError("n must be >= 1 (default 3)")
    if top < 1:
        raise CorpusError("top must be >= 1")
    if max_body_chars < 1000:
        raise CorpusError("max_body_chars must be >= 1000")

    bag_summary = load_bagit_corpus(corpus_dir, write_review_if_missing=False)
    bag_root, metadata_dir, selected = _resolve_paper_selection(
        bag_summary, paper_ids, corpus_dir
    )

    phrases_dir = phrases_dir_for_corpus(corpus_dir)
    phrases_dir.mkdir(parents=True, exist_ok=True)
    fields: List[str] = []
    if include_front_matter:
        fields.append("title+abstract")
    if include_xml_body:
        fields.append("xml_body")
    text_fields = "+".join(fields) if fields else "empty"
    params: Dict[str, Any] = {
        "method": method,
        "lan": lan if method == "yake" else None,
        "n": n,
        "top": top,
        "text_fields": text_fields,
        "include_front_matter": include_front_matter,
        "max_body_chars": max_body_chars if include_xml_body else 0,
        # Bump when phrase JSON shape changes (forces cache refresh).
        "phrase_schema": 2,
    }

    if method == "tfidf":
        return _extract_tfidf(
            corpus_dir=corpus_dir,
            bag_root=bag_root,
            metadata_dir=metadata_dir,
            selected=selected,
            phrases_dir=phrases_dir,
            params=params,
            n=n,
            top=top,
            use_cache=use_cache,
            force=force,
            include_xml_body=include_xml_body,
            include_front_matter=include_front_matter,
            max_body_chars=max_body_chars,
            progress_callback=progress_callback,
        )

    return _extract_yake(
        corpus_dir=corpus_dir,
        bag_root=bag_root,
        metadata_dir=metadata_dir,
        selected=selected,
        phrases_dir=phrases_dir,
        params=params,
        lan=lan,
        n=n,
        top=top,
        use_cache=use_cache,
        force=force,
        include_xml_body=include_xml_body,
        include_front_matter=include_front_matter,
        max_body_chars=max_body_chars,
        progress_callback=progress_callback,
        extractor=extractor,
    )


def _finalize_summary(
    *,
    corpus_dir: Path,
    bag_root: Path,
    phrases_dir: Path,
    params: Dict[str, Any],
    selected: Sequence[str],
    papers_out: List[Dict[str, Any]],
    from_cache: int,
    extracted: int,
    empty_text: int,
    total_phrases: int,
    t0: float,
    score_higher_is_better: bool,
) -> Dict[str, Any]:
    index = {
        "step": 2,
        "corpus_dir": str(corpus_dir.resolve()),
        "bag_root": str(bag_root.resolve()),
        "phrases_dir": str(phrases_dir.resolve()),
        "params": params,
        "paper_count": len(selected),
        "papers_from_cache": from_cache,
        "papers_extracted": extracted,
        "papers_empty_text": empty_text,
        "total_phrase_mentions": total_phrases,
        "unique_phrases": len(
            {p["phrase"] for rec in papers_out for p in (rec.get("phrases") or [])}
        ),
        "elapsed_s": round(time.perf_counter() - t0, 4),
        "paper_ids": list(selected),
    }
    index_path = Path(phrases_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                **index,
                "papers": [
                    {
                        "paper_id": p["paper_id"],
                        "phrase_count": p["phrase_count"],
                        "source": p["source"],
                        "cache_path": p["cache_path"],
                    }
                    for p in papers_out
                ],
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    phrases_csv = write_phrases_csv(phrases_dir, papers_out)
    summary_csv, terms_csv = write_phrases_summary_csv(
        phrases_dir,
        papers_out,
        score_higher_is_better=score_higher_is_better,
    )
    return {
        **index,
        "index_path": str(index_path.resolve()),
        "phrases_csv": str(phrases_csv.resolve()),
        "phrases_summary_csv": str(summary_csv.resolve()),
        "phrases_terms_csv": str(terms_csv.resolve()),
        "papers": papers_out,
        "step": 2,
    }


def _extract_tfidf(
    *,
    corpus_dir: Path,
    bag_root: Path,
    metadata_dir: Path,
    selected: List[str],
    phrases_dir: Path,
    params: Dict[str, Any],
    n: int,
    top: int,
    use_cache: bool,
    force: bool,
    include_xml_body: bool,
    include_front_matter: bool,
    max_body_chars: int,
    progress_callback: Optional[ProgressCallback],
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    # TF-IDF is corpus-relative: use cache only when every paper matches params.
    cacheable = use_cache and not force
    cached_records: Dict[str, Dict[str, Any]] = {}
    if cacheable:
        all_ok = True
        for paper_id in selected:
            record = load_cached_phrases(phrase_cache_path(phrases_dir, paper_id))
            if record is None or not _cache_matches_params(record, params):
                all_ok = False
                break
            cached_records[paper_id] = record
        if all_ok:
            papers_out: List[Dict[str, Any]] = []
            total_phrases = 0
            for i, paper_id in enumerate(selected):
                record = cached_records[paper_id]
                phrase_list = record.get("phrases") or []
                total_phrases += len(phrase_list)
                cache_path = phrase_cache_path(phrases_dir, paper_id)
                elapsed = float(record.get("elapsed_s") or 0.0)
                papers_out.append(
                    {
                        "paper_id": paper_id,
                        "phrase_count": len(phrase_list),
                        "phrases": phrase_list,
                        "source": "cache",
                        "elapsed_s": elapsed,
                        "cache_path": str(cache_path.resolve()),
                        "text_source": record.get("text_source") or "",
                    }
                )
                if progress_callback is not None:
                    progress_callback(i + 1, len(selected), paper_id, elapsed)
            return _finalize_summary(
                corpus_dir=corpus_dir,
                bag_root=bag_root,
                phrases_dir=phrases_dir,
                params=params,
                selected=selected,
                papers_out=papers_out,
                from_cache=len(selected),
                extracted=0,
                empty_text=0,
                total_phrases=total_phrases,
                t0=t0,
                score_higher_is_better=True,
            )

    # Build texts for all selected papers, then one TF-IDF fit.
    texts: List[str] = []
    text_sources: List[str] = []
    empty_text = 0
    for paper_id in selected:
        metadata = _load_metadata(metadata_dir, paper_id)
        built = build_phrase_input_text(
            metadata,
            bag_root=bag_root,
            paper_id=paper_id,
            include_xml_body=include_xml_body,
            include_front_matter=include_front_matter,
            max_body_chars=max_body_chars,
        )
        texts.append(built["text"])
        text_sources.append(built["text_source"])
        if not built["text"]:
            empty_text += 1

    fit_started = time.perf_counter()
    # Pull a wider TF-IDF pool; proper phrases claim reserved slots afterward.
    all_tfidf = tfidf_phrases_for_corpus(texts, n=n, top=max(top * 2, 30))
    fit_elapsed = time.perf_counter() - fit_started
    per_paper_elapsed = fit_elapsed / max(len(selected), 1)

    papers_out = []
    total_phrases = 0
    for i, paper_id in enumerate(selected):
        proper = proper_phrases_from_text(texts[i], min_count=2, top=20)
        phrases = attach_phrase_displays(
            merge_tfidf_and_proper(all_tfidf[i], proper, top=top),
            texts[i],
        )
        cache_path = phrase_cache_path(phrases_dir, paper_id)
        save_paper_phrases(
            cache_path,
            paper_id=paper_id,
            phrases=phrases,
            text_source=text_sources[i],
            params=params,
            elapsed_s=per_paper_elapsed,
        )
        total_phrases += len(phrases)
        papers_out.append(
            {
                "paper_id": paper_id,
                "phrase_count": len(phrases),
                "phrases": phrases,
                "source": "extracted",
                "elapsed_s": per_paper_elapsed,
                "cache_path": str(cache_path.resolve()),
                "text_source": text_sources[i],
            }
        )
        if progress_callback is not None:
            progress_callback(i + 1, len(selected), paper_id, per_paper_elapsed)

    return _finalize_summary(
        corpus_dir=corpus_dir,
        bag_root=bag_root,
        phrases_dir=phrases_dir,
        params=params,
        selected=selected,
        papers_out=papers_out,
        from_cache=0,
        extracted=len(selected),
        empty_text=empty_text,
        total_phrases=total_phrases,
        t0=t0,
        score_higher_is_better=True,
    )


def _extract_yake(
    *,
    corpus_dir: Path,
    bag_root: Path,
    metadata_dir: Path,
    selected: List[str],
    phrases_dir: Path,
    params: Dict[str, Any],
    lan: str,
    n: int,
    top: int,
    use_cache: bool,
    force: bool,
    include_xml_body: bool,
    include_front_matter: bool,
    max_body_chars: int,
    progress_callback: Optional[ProgressCallback],
    extractor: Any,
) -> Dict[str, Any]:
    active_extractor = extractor
    papers_out: List[Dict[str, Any]] = []
    from_cache = 0
    extracted = 0
    empty_text = 0
    total_phrases = 0
    t0 = time.perf_counter()

    for i, paper_id in enumerate(selected):
        cache_path = phrase_cache_path(phrases_dir, paper_id)
        started = time.perf_counter()
        record: Optional[Dict[str, Any]] = None

        if use_cache and not force:
            record = load_cached_phrases(cache_path)
            if record is not None and not _cache_matches_params(record, params):
                record = None

        if record is not None:
            from_cache += 1
            source = "cache"
            elapsed = float(record.get("elapsed_s") or 0.0)
        else:
            metadata = _load_metadata(metadata_dir, paper_id)
            built = build_phrase_input_text(
                metadata,
                bag_root=bag_root,
                paper_id=paper_id,
                include_xml_body=include_xml_body,
                include_front_matter=include_front_matter,
                max_body_chars=max_body_chars,
            )
            text = built["text"]
            text_source = built["text_source"]
            if not text:
                empty_text += 1
                phrases: List[Dict[str, Any]] = []
            else:
                if active_extractor is None:
                    active_extractor = _make_yake_extractor(lan=lan, n=n, top=top)
                phrases = attach_phrase_displays(
                    extract_phrases_from_text(
                        text, lan=lan, n=n, top=top, extractor=active_extractor
                    ),
                    text,
                )
            elapsed = time.perf_counter() - started
            save_paper_phrases(
                cache_path,
                paper_id=paper_id,
                phrases=phrases,
                text_source=text_source,
                params=params,
                elapsed_s=elapsed,
            )
            record = load_cached_phrases(cache_path) or {
                "paper_id": paper_id,
                "phrases": phrases,
                "phrase_count": len(phrases),
                "text_source": text_source,
                "elapsed_s": elapsed,
            }
            extracted += 1
            source = "extracted"

        phrase_list = record.get("phrases") or []
        total_phrases += len(phrase_list)
        papers_out.append(
            {
                "paper_id": paper_id,
                "phrase_count": len(phrase_list),
                "phrases": phrase_list,
                "source": source,
                "elapsed_s": float(record.get("elapsed_s") or elapsed),
                "cache_path": str(cache_path.resolve()),
                "text_source": record.get("text_source") or "",
            }
        )
        if progress_callback is not None:
            progress_callback(i + 1, len(selected), paper_id, elapsed)

    return _finalize_summary(
        corpus_dir=corpus_dir,
        bag_root=bag_root,
        phrases_dir=phrases_dir,
        params=params,
        selected=selected,
        papers_out=papers_out,
        from_cache=from_cache,
        extracted=extracted,
        empty_text=empty_text,
        total_phrases=total_phrases,
        t0=t0,
        score_higher_is_better=False,
    )


def extract_yake_phrases(
    corpus_dir: Path,
    *,
    lan: str = DEFAULT_LAN,
    n: int = DEFAULT_N,
    top: int = DEFAULT_TOP,
    use_cache: bool = True,
    force: bool = False,
    paper_ids: Optional[Sequence[str]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    extractor: Any = None,
    include_xml_body: bool = True,
    include_front_matter: bool = False,
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS,
    query_string: str = "",  # retained for API compat; ignored (no seeds)
) -> Dict[str, Any]:
    """Extract YAKE phrases (Step 2 fallback). Prefer ``extract_phrases(method='tfidf')``."""
    del query_string  # no seeds
    return extract_phrases(
        corpus_dir,
        method="yake",
        lan=lan,
        n=n,
        top=top,
        use_cache=use_cache,
        force=force,
        paper_ids=paper_ids,
        progress_callback=progress_callback,
        extractor=extractor,
        include_xml_body=include_xml_body,
        include_front_matter=include_front_matter,
        max_body_chars=max_body_chars,
    )


def extract_tfidf_phrases(
    corpus_dir: Path,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Extract corpus TF-IDF phrases (Step 2 default)."""
    kwargs.pop("method", None)
    kwargs.pop("lan", None)
    kwargs.pop("extractor", None)
    kwargs.pop("query_string", None)
    return extract_phrases(corpus_dir, method="tfidf", **kwargs)


def load_phrase_index(corpus_dir: Path) -> Optional[Dict[str, Any]]:
    """Load ``phrases/index.json`` if present."""
    path = Path(corpus_dir, "phrases", "index.json")
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
