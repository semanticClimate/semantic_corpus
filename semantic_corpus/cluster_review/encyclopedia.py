"""Encyclopedia step: resolve retained phrases to Wikipedia / Wikidata.

See ``docs/pipeline_encyclopedia.md``.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from semantic_corpus.core.exceptions import CorpusError

TERMINAL_OK = frozenset({"resolved", "ambiguous", "missing"})
STATUSES = frozenset({"resolved", "ambiguous", "missing", "error"})


def encyclopedia_dir(workdir: Path) -> Path:
    return Path(workdir) / "encyclopedia"


def entries_path(workdir: Path) -> Path:
    return encyclopedia_dir(workdir) / "entries.json"


def fetch_log_path(workdir: Path) -> Path:
    return encyclopedia_dir(workdir) / "fetch_log.jsonl"


def load_entries(workdir: Path) -> Optional[Dict[str, Any]]:
    path = entries_path(workdir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _phrase_fingerprint(phrases: Sequence[str]) -> str:
    blob = "\n".join(sorted(phrases))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _scores_from_phrases_terms(
    workdir: Path,
    *,
    demoted: set,
    min_paper_count: int = 1,
) -> Tuple[Dict[str, float], Dict[str, str], Dict[str, int]]:
    """Load unique terms from ``phrases/phrases_terms.csv`` when present."""
    import csv

    scores: Dict[str, float] = {}
    displays: Dict[str, str] = {}
    n_papers_map: Dict[str, int] = {}
    path = workdir / "phrases" / "phrases_terms.csv"
    if not path.is_file():
        return scores, displays, n_papers_map
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            phrase = str(row.get("phrase") or "").strip().lower()
            if not phrase or phrase in demoted:
                continue
            try:
                n_papers = int(float(row.get("n_papers") or 0))
            except (TypeError, ValueError):
                n_papers = 0
            if n_papers < int(min_paper_count):
                continue
            raw = row.get("best_score")
            if raw in (None, ""):
                # Prefer channel columns when best_score empty
                for key in ("best_uppercase", "best_tfidf", "best_yake"):
                    if row.get(key) not in (None, ""):
                        raw = row.get(key)
                        break
            try:
                score = abs(float(raw)) if raw not in (None, "") else float(n_papers)
            except (TypeError, ValueError):
                score = float(n_papers)
            scores[phrase] = score
            displays[phrase] = str(row.get("display") or phrase)
            n_papers_map[phrase] = n_papers
    return scores, displays, n_papers_map


def _scores_from_phrase_caches(
    workdir: Path,
    *,
    demoted: set,
    keep_papers: Optional[set],
) -> Tuple[Dict[str, float], Dict[str, str]]:
    scores: Dict[str, float] = {}
    displays: Dict[str, str] = {}
    phrases_dir = workdir / "phrases"
    if not phrases_dir.is_dir():
        return scores, displays
    for cache in sorted(phrases_dir.glob("*.json")):
        if cache.name == "index.json":
            continue
        try:
            record = json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        paper_id = str(record.get("paper_id") or cache.stem)
        if keep_papers is not None and paper_id not in keep_papers:
            continue
        for item in record.get("phrases") or []:
            if isinstance(item, dict):
                phrase = str(item.get("phrase") or "").strip().lower()
                score = float(item.get("score") or 0.0)
                disp = item.get("display") or phrase
            else:
                phrase = str(item).strip().lower()
                score = 1.0
                disp = phrase
            if not phrase or phrase in demoted:
                continue
            scores[phrase] = scores.get(phrase, 0.0) + abs(score)
            displays[phrase] = str(disp)
    return scores, displays


def _document_ids_capped(workdir: Path, document_limit: Optional[int]) -> Optional[set]:
    """Return up to ``document_limit`` paper ids from the bag (sorted), or None."""
    if document_limit is None:
        return None
    if int(document_limit) < 1:
        raise CorpusError("document_limit must be >= 1")
    from semantic_corpus.cluster_review.step1 import (
        _paper_ids_from_metadata_dir,
        resolve_bagit_root,
    )

    workdir = Path(workdir)
    bag = resolve_bagit_root(workdir)
    meta = Path(bag) / "data" / "metadata"
    ids = sorted(_paper_ids_from_metadata_dir(meta))
    if not ids:
        clusters = _load_json(workdir / "clusters" / "clusters.json") or {}
        seen: set = set()
        for cluster in clusters.get("clusters") or []:
            for pid in cluster.get("paper_ids") or []:
                if pid:
                    seen.add(str(pid))
        ids = sorted(seen)
    return set(ids[: int(document_limit)])


def select_phrases(
    workdir: Path,
    *,
    max_entries: int = 100,
    min_score: float = 0.0,
    min_paper_count: int = 1,
    source: str = "auto",
    document_limit: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Select and rank phrases for encyclopedia resolution.

    ``source``: ``auto`` (clusters if present, else phrases), ``clusters``,
    or ``phrases`` (prefer ``phrases_terms.csv``, else per-paper caches).

    ``min_paper_count`` applies when reading ``phrases_terms.csv`` (``n_papers``).
    ``max_entries`` / phrase_limit caps how many phrases are resolved.
    ``document_limit`` restricts which papers contribute (first N bag ids).

    Returns ``(candidates, phrase_source)`` where each candidate is
    ``{phrase, display, score, n_papers?}`` and ``phrase_source`` is
    ``clean`` | ``clusters`` | ``phrases`` | ``phrases_terms``.
    """
    if max_entries < 1:
        raise CorpusError("max_entries must be >= 1")
    if min_paper_count < 1:
        raise CorpusError("min_paper_count must be >= 1")
    source = (source or "auto").strip().lower()
    if source not in {"auto", "clusters", "phrases"}:
        raise CorpusError("source must be auto|clusters|phrases")

    workdir = Path(workdir)
    demoted: set = set()
    demoted_path = workdir / "clusters" / "demoted_terms.json"
    if demoted_path.is_file():
        raw = _load_json(demoted_path) or {}
        terms = raw.get("terms") or raw.get("demoted") or []
        demoted = {str(t).lower().strip() for t in terms if str(t).strip()}

    keep_papers: Optional[set] = _document_ids_capped(workdir, document_limit)
    review_path = workdir / "review" / "review_table.json"
    if review_path.is_file():
        review_raw = json.loads(review_path.read_text(encoding="utf-8"))
        if isinstance(review_raw, list):
            rows = review_raw
        elif isinstance(review_raw, dict):
            rows = review_raw.get("rows") or review_raw.get("papers") or []
        else:
            rows = []
        if isinstance(rows, list) and rows:
            reviewed: set = set()
            saw_exclude_or_keep = False
            for row in rows:
                if not isinstance(row, dict):
                    continue
                decision = (
                    row.get("decision")
                    or row.get("include")
                    or row.get("review_status")
                    or ""
                )
                decision = str(decision).lower()
                pid = row.get("paper_id") or row.get("id")
                if decision in ("exclude", "remove", "no"):
                    saw_exclude_or_keep = True
                    continue
                if decision in ("include", "keep", "yes"):
                    saw_exclude_or_keep = True
                    if pid:
                        reviewed.add(str(pid))
                elif pid:
                    # review / unsure / empty: still a candidate paper
                    reviewed.add(str(pid))
            # If nothing was explicitly keep/exclude, don't filter by review table
            if saw_exclude_or_keep:
                keep_papers = (
                    reviewed
                    if keep_papers is None
                    else (keep_papers & reviewed)
                )

    scores: Dict[str, float] = {}
    displays: Dict[str, str] = {}
    n_papers_map: Dict[str, int] = {}
    phrase_source = "phrases"

    use_clusters = source in {"auto", "clusters"}
    force_phrases = source == "phrases"
    clusters_doc = _load_json(workdir / "clusters" / "clusters.json")
    if (
        use_clusters
        and not force_phrases
        and clusters_doc
        and isinstance(clusters_doc.get("clusters"), list)
    ):
        phrase_source = "clusters"
        for cluster in clusters_doc["clusters"]:
            papers = set(cluster.get("paper_ids") or [])
            if keep_papers is not None and papers and not (papers & keep_papers):
                continue
            for term in cluster.get("terms") or []:
                phrase = str(term.get("phrase") or "").strip().lower()
                if not phrase or phrase in demoted:
                    continue
                weight = float(term.get("weight") or 0.0)
                scores[phrase] = scores.get(phrase, 0.0) + weight
                disp = term.get("display") or phrase
                displays[phrase] = str(disp)

    if scores and (demoted or keep_papers is not None):
        phrase_source = "clean"

    if not scores or force_phrases:
        terms_scores, terms_displays, n_papers_map = _scores_from_phrases_terms(
            workdir, demoted=demoted, min_paper_count=min_paper_count
        )
        if terms_scores:
            phrase_source = "phrases_terms"
            scores, displays = terms_scores, terms_displays
        else:
            phrase_source = "phrases"
            scores, displays = _scores_from_phrase_caches(
                workdir, demoted=demoted, keep_papers=keep_papers
            )
            n_papers_map = {}
        if demoted or keep_papers is not None:
            phrase_source = "clean"

    filtered = [
        (phrase, score)
        for phrase, score in scores.items()
        if score >= float(min_score)
    ]
    ranked = sorted(filtered, key=lambda kv: (-kv[1], kv[0]))[: int(max_entries)]
    candidates = []
    for phrase, score in ranked:
        row: Dict[str, Any] = {
            "phrase": phrase,
            "display": displays.get(phrase) or phrase,
            "score": round(score, 6),
        }
        if phrase in n_papers_map:
            row["n_papers"] = int(n_papers_map[phrase])
        candidates.append(row)
    return candidates, phrase_source


def _wiki_api_url(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def resolve_phrase_wikipedia(
    phrase: str,
    *,
    lang: str = "en",
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Resolve one phrase via MediaWiki search + pageprops (Wikidata id)."""
    sess = session or requests.Session()
    # Wikimedia requires a descriptive UA (403 Forbidden otherwise).
    sess.headers.update(
        {
            "User-Agent": (
                "semantic_corpus/0.1 "
                "(https://github.com/semanticClimate/semantic_corpus; "
                "contact@semanticclimate.org)"
            ),
            "Accept": "application/json",
        }
    )
    display = phrase
    base = {
        "phrase": phrase.strip().lower(),
        "display": display,
        "wiki_lang": lang,
        "wiki_title": None,
        "wiki_pageid": None,
        "wiki_url": None,
        "wikidata_id": None,
        "wikidata_url": None,
        "candidates": [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        search = sess.get(
            _wiki_api_url(lang),
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": phrase,
                "srlimit": 5,
                "srnamespace": 0,
            },
            timeout=timeout,
        )
        search.raise_for_status()
        hits = (search.json().get("query") or {}).get("search") or []
        if not hits:
            return {**base, "status": "missing"}

        candidates = [
            {
                "title": h.get("title"),
                "pageid": h.get("pageid"),
                "snippet": h.get("snippet"),
            }
            for h in hits
        ]
        base["candidates"] = candidates

        # Exact / near-exact title match preferred
        phrase_cmp = phrase.strip().lower()
        best = None
        for h in hits:
            title = str(h.get("title") or "")
            if title.lower() == phrase_cmp:
                best = h
                break
        if best is None:
            best = hits[0]

        title = str(best.get("title") or "")
        pageid = best.get("pageid")
        wiki_url = (
            f"https://{lang}.wikipedia.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"))
        )

        # Ambiguous if several strong hits and no exact title match
        exact = any(
            str(h.get("title") or "").lower() == phrase_cmp for h in hits
        )
        status = "resolved"
        if len(hits) > 1 and not exact:
            status = "ambiguous"

        wikidata_id = None
        props = sess.get(
            _wiki_api_url(lang),
            params={
                "action": "query",
                "format": "json",
                "prop": "pageprops",
                "titles": title,
                "redirects": 1,
            },
            timeout=timeout,
        )
        props.raise_for_status()
        pages = (props.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            if "missing" in page:
                continue
            pageid = page.get("pageid") or pageid
            title = page.get("title") or title
            pp = page.get("pageprops") or {}
            wikidata_id = pp.get("wikibase_item") or wikidata_id

        wiki_url = (
            f"https://{lang}.wikipedia.org/wiki/"
            + urllib.parse.quote(str(title).replace(" ", "_"))
        )
        return {
            **base,
            "status": status,
            "wiki_title": title,
            "wiki_pageid": pageid,
            "wiki_url": wiki_url,
            "wikidata_id": wikidata_id,
            "wikidata_url": (
                f"https://www.wikidata.org/wiki/{wikidata_id}" if wikidata_id else None
            ),
            "display": title or display,
        }
    except requests.RequestException as exc:
        return {
            **base,
            "status": "error",
            "error": str(exc),
            "candidates": base.get("candidates") or [],
        }


def _append_log(workdir: Path, record: Dict[str, Any]) -> None:
    path = fetch_log_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_encyclopedia(
    workdir: Path,
    *,
    lang: str = "en",
    max_entries: int = 100,
    min_score: float = 0.0,
    min_paper_count: int = 1,
    source: str = "auto",
    document_limit: Optional[int] = None,
    force: bool = False,
    sleep_s: float = 0.2,
    write_html: bool = True,
    fetch_html_descriptions: bool = True,
    html_title: Optional[str] = None,
    disambiguate: bool = True,
) -> Dict[str, Any]:
    """Select phrases and resolve encyclopedia entries under ``workdir``.

    Always calls the live MediaWiki / Wikipedia API (no injectable fakes).
    When ``write_html`` is True, also builds ``encyclopedia/encyclopedia.html``
    via the sibling ``encyclopedia`` package (AmiEncyclopedia).
    When ``disambiguate`` is True, ambiguous / dab-page hits are resolved with
    ``encyclopedia.pipeline.wikipedia_disambiguation`` using paper sentences.
    """
    workdir = Path(workdir)
    if not lang or not str(lang).strip():
        raise CorpusError("lang is required")

    candidates, phrase_source = select_phrases(
        workdir,
        max_entries=max_entries,
        min_score=min_score,
        min_paper_count=min_paper_count,
        source=source,
        document_limit=document_limit,
    )
    selected_ids = [c["phrase"] for c in candidates]
    fingerprint = _phrase_fingerprint(selected_ids)

    contexts_by_phrase: Dict[str, List[str]] = {}
    if disambiguate and selected_ids:
        from semantic_corpus.cluster_review.encyclopedia_disambiguation import (
            collect_phrase_context_sentences,
        )

        contexts_by_phrase = collect_phrase_context_sentences(
            workdir, selected_ids
        )

    existing = load_entries(workdir) or {}
    by_phrase: Dict[str, Dict[str, Any]] = {}
    for entry in existing.get("entries") or []:
        if isinstance(entry, dict) and entry.get("phrase"):
            by_phrase[str(entry["phrase"]).lower()] = entry

    out_entries: List[Dict[str, Any]] = []
    n_fetched = 0
    n_cached = 0
    n_error = 0
    n_disambiguated = 0

    for cand in candidates:
        phrase = cand["phrase"]
        prev = by_phrase.get(phrase)
        if (
            not force
            and prev
            and prev.get("status") in TERMINAL_OK
            and prev.get("wiki_lang", lang) == lang
        ):
            # Preserve display preference from selection when missing
            if not prev.get("display"):
                prev = {**prev, "display": cand.get("display") or phrase}
            out_entries.append(prev)
            n_cached += 1
            _append_log(
                workdir,
                {
                    "phrase": phrase,
                    "action": "cache_hit",
                    "status": prev.get("status"),
                    "ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            continue

        result = resolve_phrase_wikipedia(phrase, lang=lang)
        result["phrase"] = phrase
        if not result.get("display"):
            result["display"] = cand.get("display") or phrase
        if result.get("status") == "missing":
            result["display"] = cand.get("display") or phrase
        elif cand.get("display") and result.get("status") == "error":
            result["display"] = cand.get("display")

        if disambiguate and result.get("status") != "error":
            from semantic_corpus.cluster_review.encyclopedia_disambiguation import (
                apply_encyclopedia_disambiguation,
                needs_disambiguation,
            )

            if needs_disambiguation(result):
                sentences = contexts_by_phrase.get(phrase) or []
                before = result.get("wiki_title")
                result = apply_encyclopedia_disambiguation(
                    result,
                    sentences=sentences,
                    lang=lang,
                )
                if (
                    result.get("disambiguation_status") == "resolved"
                    and result.get("wiki_title") != before
                ):
                    n_disambiguated += 1

        out_entries.append(result)
        n_fetched += 1
        if result.get("status") == "error":
            n_error += 1
        _append_log(
            workdir,
            {
                "phrase": phrase,
                "action": "fetch",
                "status": result.get("status"),
                "wiki_title": result.get("wiki_title"),
                "wikidata_id": result.get("wikidata_id"),
                "disambiguation_status": result.get("disambiguation_status"),
                "disambiguation_history": result.get("disambiguation_history"),
                "detail": result.get("error"),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )
        if sleep_s > 0:
            time.sleep(sleep_s)

    params = {
        "lang": lang,
        "max_entries": int(max_entries),
        "min_score": float(min_score),
        "min_paper_count": int(min_paper_count),
        "document_limit": (
            int(document_limit) if document_limit is not None else None
        ),
        "source": source,
        "phrase_source": phrase_source,
        "selected_count": len(selected_ids),
        "phrase_fingerprint": fingerprint,
        "disambiguate": bool(disambiguate),
    }
    doc = {
        "step": "encyclopedia",
        "workdir": str(workdir.resolve()),
        "params": params,
        "entries": out_entries,
        "counts": {
            "selected": len(selected_ids),
            "written": len(out_entries),
            "fetched": n_fetched,
            "cached": n_cached,
            "error": n_error,
            "resolved": sum(1 for e in out_entries if e.get("status") == "resolved"),
            "ambiguous": sum(1 for e in out_entries if e.get("status") == "ambiguous"),
            "missing": sum(1 for e in out_entries if e.get("status") == "missing"),
            "disambiguated": n_disambiguated,
        },
    }

    out_dir = encyclopedia_dir(workdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = entries_path(workdir)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    doc["entries_path"] = str(path.resolve())

    if write_html:
        from semantic_corpus.cluster_review.encyclopedia_html import (
            write_encyclopedia_html,
        )

        html_out = write_encyclopedia_html(
            workdir,
            entries_doc=doc,
            title=html_title or f"Encyclopedia ({workdir.name})",
            fetch_descriptions=fetch_html_descriptions,
        )
        doc["html_path"] = str(html_out.resolve())
        # Persist html path in entries.json for consumers / uptodate
        path.write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return doc


def encyclopedia_is_current(
    workdir: Path,
    *,
    lang: str,
    max_entries: int,
    min_score: float = 0.0,
    min_paper_count: int = 1,
    source: str = "auto",
    document_limit: Optional[int] = None,
    require_html: bool = True,
) -> bool:
    """True when entries.json matches options and phrase fingerprint."""
    doc = load_entries(workdir)
    if not doc:
        return False
    params = doc.get("params") or {}
    if params.get("lang") != lang:
        return False
    if int(params.get("max_entries") or 0) != int(max_entries):
        return False
    if float(params.get("min_score") or 0.0) != float(min_score):
        return False
    stored_min_papers = params.get("min_paper_count", params.get("min_papers", 1))
    if int(stored_min_papers or 1) != int(min_paper_count):
        return False
    if str(params.get("source") or "auto") != str(source):
        return False
    stored_doc_limit = params.get("document_limit")
    if (stored_doc_limit is None) != (document_limit is None):
        return False
    if document_limit is not None and int(stored_doc_limit or 0) != int(
        document_limit
    ):
        return False
    if require_html:
        from semantic_corpus.cluster_review.encyclopedia_html import html_path

        if not html_path(workdir).is_file():
            return False
    candidates, _source = select_phrases(
        workdir,
        max_entries=max_entries,
        min_score=min_score,
        min_paper_count=min_paper_count,
        source=source,
        document_limit=document_limit,
    )
    selected_ids = [c["phrase"] for c in candidates]
    expected = _phrase_fingerprint(selected_ids)
    return params.get("phrase_fingerprint") == expected
