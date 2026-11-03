"""Automatic Wikipedia disambiguation via the sibling ``encyclopedia`` package.

Uses ``encyclopedia.pipeline.wikipedia_disambiguation.resolve_disambiguation``
with paper sentences collected from the corpus (XML body / phrase input text).
"""

from __future__ import annotations

import csv
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import requests

from semantic_corpus.core.exceptions import CorpusError

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return " ".join(_TAG_RE.sub(" ", text or "").split())


def _phrase_key(term: str) -> str:
    return " ".join(str(term or "").lower().split())


def collect_phrase_context_sentences(
    workdir: Path,
    phrases: Sequence[str],
    *,
    max_per_phrase: int = 25,
    max_body_chars: int = 50_000,
) -> Dict[str, List[str]]:
    """Collect paper sentences that mention each phrase (case-insensitive).

    Prefers ``phrases/phrases_terms.csv`` paper_ids; falls back to all phrase
    JSON caches. Sentence text comes from Step-2 body text when available.
    """
    workdir = Path(workdir)
    wanted = {_phrase_key(p): p for p in phrases if str(p).strip()}
    if not wanted:
        return {}

    paper_to_phrases: Dict[str, List[str]] = {}
    terms_csv = workdir / "phrases" / "phrases_terms.csv"
    if terms_csv.is_file():
        with open(terms_csv, "r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = _phrase_key(row.get("phrase") or "")
                if key not in wanted:
                    continue
                for pid in str(row.get("paper_ids") or "").split(";"):
                    pid = pid.strip()
                    if not pid:
                        continue
                    paper_to_phrases.setdefault(pid, []).append(key)

    if not paper_to_phrases:
        phrases_dir = workdir / "phrases"
        if phrases_dir.is_dir():
            import json

            for cache in phrases_dir.glob("*.json"):
                if cache.name == "index.json":
                    continue
                try:
                    record = json.loads(cache.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                pid = str(record.get("paper_id") or cache.stem)
                for item in record.get("phrases") or []:
                    if isinstance(item, dict):
                        key = _phrase_key(item.get("phrase") or "")
                    else:
                        key = _phrase_key(item)
                    if key in wanted:
                        paper_to_phrases.setdefault(pid, []).append(key)

    contexts: Dict[str, List[str]] = {k: [] for k in wanted}
    if not paper_to_phrases:
        return contexts

    from semantic_corpus.cluster_review.step1 import load_bagit_corpus
    from semantic_corpus.cluster_review.step2 import (
        _load_metadata,
        build_phrase_input_text,
    )

    try:
        bag = load_bagit_corpus(workdir, write_review_if_missing=False)
        bag_root = Path(bag["bag_root"])
        metadata_dir = Path(bag["metadata_dir"])
    except Exception:
        return contexts

    for paper_id, keys in paper_to_phrases.items():
        try:
            metadata = _load_metadata(metadata_dir, paper_id)
            built = build_phrase_input_text(
                metadata,
                bag_root=bag_root,
                paper_id=paper_id,
                include_xml_body=True,
                include_front_matter=False,
                max_body_chars=max_body_chars,
            )
            text = built.get("text") or ""
        except Exception:
            continue
        if not text:
            continue
        sentences = _SENTENCE_SPLIT.split(text)
        unique_keys = list(dict.fromkeys(keys))
        for key in unique_keys:
            bucket = contexts[key]
            if len(bucket) >= max_per_phrase:
                continue
            needle = key
            for sent in sentences:
                if needle in sent.lower():
                    cleaned = " ".join(sent.split())
                    if cleaned and cleaned not in bucket:
                        bucket.append(cleaned)
                    if len(bucket) >= max_per_phrase:
                        break

    # Re-key to original phrase spellings when possible
    out: Dict[str, List[str]] = {}
    for key, original in wanted.items():
        out[original] = contexts.get(key) or []
        out[key] = out[original]
    return out


def _is_disambiguation_title(title: Optional[str]) -> bool:
    t = (title or "").lower()
    return "(disambiguation)" in t


def needs_disambiguation(entry: Mapping[str, Any]) -> bool:
    """True when search was ambiguous or the hit is a dab page."""
    status = str(entry.get("status") or "")
    if status == "ambiguous":
        return True
    if _is_disambiguation_title(entry.get("wiki_title")):
        return True
    return False


def _candidates_html(entry: Mapping[str, Any], phrase: str) -> str:
    from encyclopedia.pipeline.wikipedia_disambiguation import (
        disambiguation_page_html,
    )

    items: List[Tuple[str, str]] = []
    for cand in entry.get("candidates") or []:
        title = str(cand.get("title") or "").strip()
        if not title or _is_disambiguation_title(title):
            continue
        gloss = _strip_html(str(cand.get("snippet") or ""))
        items.append((title, gloss))
    if not items and entry.get("wiki_title"):
        items.append((str(entry["wiki_title"]), ""))
    intro = f"{phrase} may refer to:"
    return disambiguation_page_html(intro, items)


def _fetch_disambiguation_html(
    title: str,
    *,
    lang: str,
    session: requests.Session,
    timeout: float = 30.0,
) -> Optional[str]:
    try:
        resp = session.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "parse",
                "format": "json",
                "page": title,
                "prop": "text",
                "redirects": 1,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return ((resp.json().get("parse") or {}).get("text") or {}).get("*")
    except (requests.RequestException, ValueError, TypeError):
        return None


def _fill_from_title(
    entry: Dict[str, Any],
    title: str,
    *,
    lang: str,
    session: requests.Session,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Update entry fields for a chosen Wikipedia title."""
    out = dict(entry)
    out["wiki_title"] = title
    out["wiki_url"] = (
        f"https://{lang}.wikipedia.org/wiki/"
        + urllib.parse.quote(title.replace(" ", "_"))
    )
    out["display"] = title
    try:
        props = session.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "prop": "pageprops|info",
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
            out["wiki_pageid"] = page.get("pageid") or out.get("wiki_pageid")
            out["wiki_title"] = page.get("title") or title
            out["display"] = out["wiki_title"]
            out["wiki_url"] = (
                f"https://{lang}.wikipedia.org/wiki/"
                + urllib.parse.quote(str(out["wiki_title"]).replace(" ", "_"))
            )
            pp = page.get("pageprops") or {}
            wid = pp.get("wikibase_item")
            if wid:
                out["wikidata_id"] = wid
                out["wikidata_url"] = f"https://www.wikidata.org/wiki/{wid}"
            break
    except requests.RequestException as exc:
        out["disambiguation_error"] = str(exc)
    out["status"] = "resolved"
    return out


def apply_encyclopedia_disambiguation(
    entry: Dict[str, Any],
    *,
    sentences: Sequence[str],
    lang: str = "en",
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
    leads: Optional[Mapping[str, str]] = None,
    fill_title: bool = True,
) -> Dict[str, Any]:
    """Run encyclopedia ``resolve_disambiguation`` and update the entry.

    ``leads`` is optional (tests): title → lead paragraph, avoids lead fetch.
    ``fill_title=False`` skips MediaWiki pageprops fill (offline tests).
    """
    if not needs_disambiguation(entry):
        return entry

    try:
        from encyclopedia.pipeline.wikipedia_disambiguation import (
            resolve_disambiguation,
        )
    except ImportError as exc:
        raise CorpusError(
            "encyclopedia package required for disambiguation "
            "(pip install -e ../encyclopedia)"
        ) from exc

    sess = session or requests.Session()
    sess.headers.setdefault(
        "User-Agent",
        "semantic_corpus/0.1 (https://github.com/semanticClimate/semantic_corpus; "
        "contact@semanticclimate.org)",
    )

    phrase = str(entry.get("phrase") or entry.get("display") or "")
    html: Optional[str] = None
    title = entry.get("wiki_title")
    if fill_title and _is_disambiguation_title(title):
        html = _fetch_disambiguation_html(
            str(title), lang=lang, session=sess, timeout=timeout
        )
    if not html:
        html = _candidates_html(entry, phrase)

    decision = resolve_disambiguation(phrase, html, list(sentences or []), leads=leads)
    out = dict(entry)
    out["disambiguation_history"] = decision.history
    out["disambiguation_status"] = decision.status

    if decision.status == "resolved" and decision.chosen_title:
        dab_url = out.get("wiki_url")
        dab_title = out.get("wiki_title")
        if fill_title:
            out = _fill_from_title(
                out,
                decision.chosen_title,
                lang=lang,
                session=sess,
                timeout=timeout,
            )
        else:
            out["wiki_title"] = decision.chosen_title
            out["display"] = decision.chosen_title
            out["wiki_url"] = (
                f"https://{lang}.wikipedia.org/wiki/"
                + urllib.parse.quote(decision.chosen_title.replace(" ", "_"))
            )
            out["status"] = "resolved"
        out["pointer_kind"] = "disambiguation"
        out["pointer_url"] = dab_url
        out["pointer_title"] = dab_title
        out["disambiguation_history"] = decision.history
        out["disambiguation_status"] = decision.status
        return out

    if decision.status == "choice" and decision.titles:
        # Keep ambiguous but record the close pair
        out["status"] = "ambiguous"
        out["disambiguation_titles"] = list(decision.titles)
        return out

    # unresolved: leave prior status (usually ambiguous)
    if out.get("status") != "missing":
        out["status"] = "ambiguous"
    out["disambiguation_titles"] = list(decision.titles or [])
    return out
