"""Real step actions for the pipeline.

Design spine: collect → corpus → phrases → clusters[--kg] → clean → encyclopedia[--kg].
Set ``PIPELINE_PLACEHOLDER=1`` to force stamp-only behaviour (unit tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import os

from semantic_corpus.pipeline.config import (
    DEFAULT_LIMIT,
    ENV_PLACEHOLDER,
    options_from_env,
)
from semantic_corpus.pipeline.placeholders import run_placeholder, stamp_path, write_stamp


def use_placeholders() -> bool:
    return os.environ.get(ENV_PLACEHOLDER, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _stamp(step: str, extra: Optional[Dict[str, Any]] = None) -> Path:
    opts = options_from_env()
    return write_stamp(step, opts.workdir, extra={"status": "ok", **(extra or {})})


def _workdir_paths():
    """Corpus bag root (``--workdir``); packet bytes under ``data/packets/``."""
    opts = options_from_env()
    workdir = opts.workdir
    return workdir, workdir.name


def _paper_meta_from_search(workdir: Path, stem: str) -> Dict[str, Any]:
    from semantic_corpus.pipeline.flat_corpus import (
        load_paper_json,
        paper_stem,
        path_search_results,
    )

    paper_meta = load_paper_json(workdir, stem)
    if paper_meta:
        return paper_meta
    results_path = path_search_results(workdir)
    if not results_path.is_file():
        return {}
    import json

    rows = json.loads(results_path.read_text(encoding="utf-8"))
    stem_u = str(stem).strip().upper()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        candidates = (
            row.get("pmcid"),
            row.get("paper_id"),
            row.get("pmid"),
            row.get("id"),
        )
        for raw in candidates:
            if not raw:
                continue
            if paper_stem(str(raw)) == stem or str(raw).strip().upper() == stem_u:
                return row
    return {}


def _mark_xml_status(
    workdir: Path,
    stem: str,
    status: str,
    *,
    http_status: Optional[int] = None,
) -> None:
    """Record XML outcome on ``{id}.json`` so resume can stop retrying forever."""
    import json

    from semantic_corpus.pipeline.flat_corpus import find_paper_json, path_json

    path = find_paper_json(workdir, stem) or path_json(workdir, stem)
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    changed = False
    if data.get("_collect_xml") != status:
        data["_collect_xml"] = status
        changed = True
    if http_status is not None and data.get("_collect_xml_http") != int(http_status):
        data["_collect_xml_http"] = int(http_status)
        changed = True
    if not changed:
        return
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _status_label_for_paper_result(result: Dict[str, Any]) -> str:
    from semantic_corpus.pipeline.doit_reporter import status_label_from_streams

    label = status_label_from_streams(result.get("streams"))
    if label:
        return label
    if result.get("success") and result.get("xml"):
        return "ok"
    if result.get("status_code"):
        return f"xml={result['status_code']}"
    err = str(result.get("error") or "")
    if "No PMCID" in err:
        return "no_pmcid"
    return "ok" if result.get("success") else "miss"


def _record_xml_http(workdir: Path, stem: str, http_status: int) -> None:
    """Remember last XML HTTP code without marking the paper collect-done."""
    import json

    from semantic_corpus.pipeline.flat_corpus import find_paper_json, path_json

    path = find_paper_json(workdir, stem) or path_json(workdir, stem)
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    if data.get("_collect_xml_http") == int(http_status):
        return
    data["_collect_xml_http"] = int(http_status)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _http_code_from_result(result: Dict[str, Any]) -> Optional[int]:
    code = result.get("status_code")
    if code is not None:
        try:
            return int(code)
        except (TypeError, ValueError):
            pass
    for note in result.get("streams") or []:
        text = str(note)
        if text.startswith("xml-http:"):
            try:
                return int(text.split(":", 1)[1])
            except ValueError:
                return None
    return None


def run_search() -> Dict[str, Any]:
    """EPMC (etc.) search only → ``query.json`` + ``search_results.json``."""
    if use_placeholders():
        return run_placeholder("search")

    opts = options_from_env()
    if opts.query and opts.source:
        raise ValueError("Use either --query or --source, not both")
    if opts.source:
        raise NotImplementedError(
            "search --source (static documents) is not wired yet; use --query"
        )
    if not opts.query:
        raise ValueError("search requires --query")

    from semantic_corpus.core.repository_factory import RepositoryFactory
    from semantic_corpus.pipeline.flat_corpus import (
        ensure_light_bagit,
        path_query,
        path_search_results,
        write_corpus_json,
        write_json_atomic,
    )

    workdir, query_name = _workdir_paths()
    ensure_light_bagit(workdir)
    limit = int(opts.limit or DEFAULT_LIMIT)
    repo_name = opts.repository or "europe_pmc"
    print(
        f"[pipeline] search: {opts.query!r} limit={limit} "
        f"repository={repo_name!r} → {workdir}"
    )

    # Search only — no full-text download (papers are fine-grained tasks).
    repo = RepositoryFactory.get_repository(repo_name)
    results = list(repo.search_papers(query=opts.query, limit=limit) or [])[:limit]
    write_json_atomic(
        path_query(workdir),
        {
            "query": opts.query,
            "query_name": query_name,
            "limit": limit,
            "repository": repo_name,
            "result_count": len(results),
        },
    )
    write_json_atomic(path_search_results(workdir), results)
    write_corpus_json(
        workdir, query=opts.query, limit=limit, repository=repo_name
    )
    _stamp(
        "search",
        {
            "mode": "remote",
            "result_count": len(results),
            "search_results": str(path_search_results(workdir)),
        },
    )
    print(f"[pipeline] search: {len(results)} hits → {path_search_results(workdir)}")
    return {
        "result_count": len(results),
        "search_results_path": str(path_search_results(workdir)),
        "results": results,
    }


def run_paper(
    paper_id: str,
    *,
    formats: Optional[list] = None,
    use_docling_xml: bool = False,
    streams: Optional[Any] = None,
) -> Dict[str, Any]:
    """Fetch missing formats for one paper into ``data/packets/``.

    Default collect formats are JSON+XML only (no PDF). Pass ``formats=["pdf"]``
    from the lazy ``pdfs`` step. Pass a shared ``streams`` board from collect so
    HTTP 5xx are accumulated across papers.
    """
    if use_placeholders():
        return {"paper_id": paper_id, "status": "placeholder"}

    from semantic_corpus.core.repository_factory import RepositoryFactory
    from semantic_corpus.pipeline.flat_corpus import (
        ensure_light_bagit,
        find_best_xml,
        paper_collect_done,
        paper_stem,
    )
    from semantic_corpus.repositories.epmc_streams import (
        EpmcStreamBoard,
        PREFLIGHT_BOARD,
    )

    opts = options_from_env()
    workdir = opts.workdir
    ensure_light_bagit(workdir)
    stem = paper_stem(paper_id)
    fmt_list = list(formats) if formats is not None else ["xml"]

    if fmt_list == ["xml"] and paper_collect_done(workdir, stem):
        return {
            "success": True,
            "paper_id": stem,
            "skipped": True,
            "streams": ["skip-collect-done"],
            "status_label": "ok",
        }

    paper_meta = _paper_meta_from_search(workdir, stem)
    repo_name = opts.repository or "europe_pmc"
    repo = RepositoryFactory.get_repository(repo_name)
    board = streams
    if board is None:
        board = PREFLIGHT_BOARD if isinstance(PREFLIGHT_BOARD, EpmcStreamBoard) else None
    if board is None:
        board = EpmcStreamBoard()

    from semantic_corpus.core.exceptions import RepositoryError, SemanticCorpusError
    from semantic_corpus.repositories.epmc_streams import write_paper_metadata_json

    try:
        result = repo.download_paper(
            stem,
            workdir,
            formats=fmt_list,
            paper=paper_meta or None,
            streams=board,
            use_docling_xml=use_docling_xml,
        )
    except Exception as exc:
        # Soft-fail: never abort the doit graph for one paper (e.g. PMID-only).
        meta = dict(paper_meta) if paper_meta else {"paper_id": stem}
        try:
            write_paper_metadata_json(workdir, stem, meta)
        except OSError:
            pass
        msg = str(exc)
        if "No PMCID" in msg or "pmcid" in msg.lower():
            _mark_xml_status(workdir, stem, "no_pmcid")
            note = "no_pmcid"
        else:
            _mark_xml_status(workdir, stem, "unavailable")
            note = "error"
        print(f"[pipeline] paper {stem}: skip — {msg}")
        return {
            "success": False,
            "paper_id": stem,
            "skipped": True,
            "error": msg,
            "streams": [note],
            "status_label": note,
        }

    notes = " ".join(str(x) for x in (result.get("streams") or []))
    # Soft miss: no PMCID (PMID-only) or explicit failure — do not fail the doit task.
    if (not result.get("success", True)) or ("no_pmcid" in notes):
        meta = dict(paper_meta) if paper_meta else {"paper_id": stem}
        try:
            write_paper_metadata_json(workdir, stem, meta)
        except OSError:
            pass
        err = str(result.get("error") or "no_pmcid" if "no_pmcid" in notes else notes)
        http_code = _http_code_from_result(result)
        if "no_pmcid" in notes or "No PMCID" in str(err):
            _mark_xml_status(workdir, stem, "no_pmcid")
            err = result.get("error") or "No PMCID (metadata only)"
            label = "no_pmcid"
        else:
            if http_code is not None:
                _record_xml_http(workdir, stem, int(http_code))
                label = f"xml={http_code}"
            else:
                label = _status_label_for_paper_result(result)
        print(f"[pipeline] paper {stem}: skip — {err}")
        out = {
            "success": False,
            "paper_id": stem,
            "skipped": True,
            "error": err,
            "streams": result.get("streams") or ["skip"],
            "status_label": label,
        }
        if http_code is not None:
            out["status_code"] = int(http_code)
        return out

    if find_best_xml(workdir, stem) is not None:
        _mark_xml_status(workdir, stem, "ok")
        result = dict(result)
        result["status_label"] = "ok"
        result["xml"] = True
    else:
        result = dict(result)
        http_code = _http_code_from_result(result)
        if http_code is not None:
            _record_xml_http(workdir, stem, int(http_code))
        result.setdefault("status_label", _status_label_for_paper_result(result))
    # HTTP XML misses stay unmarked as done so resume can retry later.
    return result


def run_collect() -> Dict[str, Any]:
    """Search (if needed) then fetch JSON+XML per paper (no PDF); resume-friendly."""
    if use_placeholders():
        return run_placeholder("collect")

    opts = options_from_env()
    if opts.query and opts.source:
        raise ValueError("Use either --query or --source, not both")
    if opts.source:
        raise NotImplementedError(
            "collect --source (static documents) is not wired yet; "
            "use --query for remotes, or point --workdir at an existing corpus"
        )
    if not opts.query:
        from semantic_corpus.pipeline.flat_corpus import path_search_results

        if not path_search_results(opts.workdir).is_file():
            raise ValueError(
                "collect requires --query (EPMC/other remotes) or existing "
                "search_results.json under --workdir"
            )

    from semantic_corpus.pipeline.flat_corpus import (
        ensure_light_bagit,
        list_paper_ids_from_search,
        packets_dir,
        paper_collect_done,
        path_search_results,
    )

    workdir, _query_name = _workdir_paths()
    ensure_light_bagit(workdir)

    if opts.query:
        if path_search_results(workdir).is_file():
            if not stamp_path("search", workdir).is_file():
                _stamp(
                    "search",
                    {
                        "mode": "remote",
                        "result_count": len(list_paper_ids_from_search(workdir)),
                        "search_results": str(path_search_results(workdir)),
                        "reused": True,
                    },
                )
        else:
            run_search()

    paper_ids = list_paper_ids_from_search(workdir)
    pkt = packets_dir(workdir)
    print(
        f"[pipeline] collect: {len(paper_ids)} papers → JSON+XML under {pkt} "
        f"(PDFs deferred to --target pdfs)"
    )

    from semantic_corpus.corpus_review.collect_progress import (
        CollectTitleScroller,
        title_from_paper,
    )
    from semantic_corpus.repositories import epmc_streams as streams_mod
    from semantic_corpus.repositories.epmc_streams import (
        EpmcStreamBoard,
        print_stream_board,
    )

    board = streams_mod.PREFLIGHT_BOARD
    if not isinstance(board, EpmcStreamBoard):
        board = EpmcStreamBoard()
        streams_mod.PREFLIGHT_BOARD = board

    scroller = CollectTitleScroller(limit=max(len(paper_ids), 1))
    scroller.start(query=opts.query or "", repository=opts.repository or "europe_pmc")
    ok = 0
    skipped = 0
    for pid in paper_ids:
        if paper_collect_done(workdir, pid):
            ok += 1
            skipped += 1
            scroller.add(title=pid, paper_id=pid, status="skip", reason="exists")
            continue
        try:
            result = run_paper(
                pid,
                formats=["xml"],
                use_docling_xml=False,
                streams=board,
            )
            meta = result if isinstance(result, dict) else {}
            title = title_from_paper(meta) if meta else pid
            if paper_collect_done(workdir, pid):
                ok += 1
                scroller.add(title=title or pid, paper_id=pid, status="ok")
            else:
                scroller.add(
                    title=title or pid,
                    paper_id=pid,
                    status="fail",
                    reason="incomplete",
                )
        except Exception as exc:
            scroller.add(
                title=pid, paper_id=pid, status="fail", reason=str(exc)[:80]
            )
            print(f"[pipeline] collect: paper {pid} failed: {exc}")
    scroller.finish(downloaded=ok, skipped=skipped)

    print_stream_board(board, final=True)
    report_path = board.write_error_report(
        workdir / "pipeline" / "epmc_http_errors.json"
    )
    xml_errs = board.errors_for("xml")
    status_tally = board.format_status_counts() or "none"
    print(
        f"[pipeline] collect: EPMC HTTP errors {status_tally} → {report_path} "
        f"(total={len(board.http_errors)}, XML={len(xml_errs)})"
    )

    summary = {
        "downloaded_count": ok,
        "result_count": len(paper_ids),
        "paper_ids": paper_ids,
        "skipped_existing": skipped,
        "epmc_http_errors": str(report_path),
        "epmc_http_error_count": len(board.http_errors),
        "epmc_xml_http_error_count": len(xml_errs),
        "epmc_http_by_status": board.error_counts_by_status(),
    }
    paper_count = ok

    index_summary = _ensure_packet_indexes(workdir)
    counts = index_summary.get("counts") or {}
    _stamp(
        "collect",
        {
            "mode": "remote",
            "workdir": str(workdir),
            "downloaded_count": summary.get("downloaded_count"),
            "paper_count": paper_count,
            "layout": "bagit_packets",
            "packets_dir": str(pkt),
            "epmc_http_errors": str(report_path),
            "epmc_xml_http_error_count": len(xml_errs),
            "epmc_http_by_status": {
                str(k): v for k, v in sorted(board.error_counts_by_status().items())
            },
        },
    )
    _stamp(
        "corpus",
        {
            "produced_by": "collect",
            "layout": "bagit_packets",
            "paper_count": paper_count,
            "packets_manifest": index_summary.get("manifest_path"),
            "containers": counts.get("containers"),
            "packets": counts.get("packets"),
        },
    )
    print(
        f"[pipeline] collect: finished "
        f"({paper_count}/{len(paper_ids)} papers; "
        f"packets={counts.get('packets')}; HTTP {status_tally}) → {pkt}"
    )
    return summary


def _ensure_packet_indexes(workdir: Path) -> Dict[str, Any]:
    """Structural indexes on text components (part of corpus, not a separate step)."""
    from semantic_corpus.cluster_review.packets import build_packet_index

    return build_packet_index(workdir)


def run_corpus() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("corpus")

    from semantic_corpus.cluster_review.step1 import load_corpus
    from semantic_corpus.pipeline.flat_corpus import is_flat_corpus, list_flat_paper_ids

    opts = options_from_env()
    workdir = opts.workdir
    has_bag = (workdir / "bagit.txt").is_file() or (
        workdir / "data" / "bagit.txt"
    ).is_file()
    if not has_bag and not is_flat_corpus(workdir):
        raise FileNotFoundError(
            f"No corpus at {workdir}. "
            "Run with --query or --source first, or point --workdir at an existing corpus."
        )
    print(f"[pipeline] corpus: loading {workdir}")
    summary = load_corpus(workdir, write_review_if_missing=True)
    print(f"[pipeline] corpus: ensuring packet indexes")
    index_summary = _ensure_packet_indexes(workdir)
    counts = index_summary.get("counts") or {}
    paper_count = summary.get("paper_count") or len(list_flat_paper_ids(workdir))
    _stamp(
        "corpus",
        {
            "paper_count": paper_count,
            "bag_root": summary.get("bag_root") or str(workdir),
            "layout": summary.get("layout") or ("bagit" if has_bag else "flat"),
            "packets_manifest": index_summary.get("manifest_path"),
            "containers": counts.get("containers"),
            "packets": counts.get("packets"),
        },
    )
    print(
        f"[pipeline] corpus: {paper_count} papers; "
        f"packets={counts.get('packets')} → {index_summary.get('manifest_path')}"
    )
    summary = dict(summary)
    summary["packet_index"] = index_summary
    return summary


def run_phrases() -> Dict[str, Any]:
    if use_placeholders():
        return run_placeholder("phrases")

    from semantic_corpus.cluster_review.step2 import extract_phrases

    opts = options_from_env()
    print(
        f"[pipeline] phrases: traverse packet texts; "
        f"method={opts.phrase_method} n={opts.phrase_n} top={opts.phrase_top}"
    )
    summary = extract_phrases(
        opts.workdir,
        method=opts.phrase_method,
        n=opts.phrase_n,
        top=opts.phrase_top,
        use_cache=True,
        force=False,
    )
    _stamp(
        "phrases",
        {
            "paper_count": summary.get("paper_count"),
            "index": str(opts.workdir / "phrases" / "index.json"),
        },
    )
    print(f"[pipeline] phrases: done ({summary.get('paper_count')} papers)")
    return summary


def run_pdfs() -> Dict[str, Any]:
    """Lazy PDF fill: fetch missing ``data/packets/{id}.pdf`` (optional Docling).

    Use after collect. Respects ``PIPELINE_PAPER_ID`` for a single-paper download.
    """
    if use_placeholders():
        return run_placeholder("pdfs")

    from semantic_corpus.pipeline.flat_corpus import (
        ensure_light_bagit,
        find_best_xml,
        find_pdf,
        list_flat_paper_ids,
        list_paper_ids_from_search,
        packets_dir,
        paper_stem,
    )

    opts = options_from_env()
    workdir = opts.workdir
    ensure_light_bagit(workdir)

    only = os.environ.get("PIPELINE_PAPER_ID", "").strip()
    if only:
        paper_ids = [paper_stem(only)]
    else:
        paper_ids = list_paper_ids_from_search(workdir) or list_flat_paper_ids(workdir)

    print(
        f"[pipeline] pdfs: {len(paper_ids)} paper(s) → {packets_dir(workdir)} "
        f"(skip existing PDFs)"
    )
    fetched = 0
    skipped = 0
    failed = 0
    docling = 0
    for pid in paper_ids:
        if find_pdf(workdir, pid) is not None:
            skipped += 1
            continue
        try:
            result = run_paper(
                pid,
                formats=["pdf"],
                use_docling_xml=find_best_xml(workdir, pid) is None,
            )
            if find_pdf(workdir, pid) is not None:
                fetched += 1
            else:
                failed += 1
            notes = result.get("streams") or []
            if any("xml-from-pdf" in str(n) for n in notes):
                docling += 1
        except Exception as exc:
            failed += 1
            print(f"[pipeline] pdfs: {pid} failed: {exc}")

    summary = {
        "paper_count": len(paper_ids),
        "fetched": fetched,
        "skipped_existing": skipped,
        "failed": failed,
        "docling_xml": docling,
        "paper_id": only or None,
    }
    _stamp("pdfs", summary)
    print(
        f"[pipeline] pdfs: fetched={fetched} skipped={skipped} "
        f"failed={failed} docling_xml={docling}"
    )
    return summary



def _emit_display_kg(stage: str) -> Optional[Dict[str, Any]]:
    """Write/open display KG after clusters (plain) or encyclopedia (annotated).

    Not a pipeline step — cheap view assembly controlled by ``--kg`` / ``--no-kg``.
    """
    opts = options_from_env()
    if not opts.write_kg:
        print(f"[pipeline] {stage}: --no-kg (skip display graph)")
        return None
    if use_placeholders():
        print(f"[pipeline] {stage}: kg placeholder (stage={stage})")
        return {"status": "placeholder", "stage": stage}

    from semantic_corpus.cluster_review.kg import build_kg

    if stage == "clusters":
        # Unannotated incidence graph only.
        links: tuple = ("clusters",)
    else:
        # Annotated: keep user --kg-links; default clusters, add wikipedia if present.
        links = opts.kg_link_list()
        enc = opts.workdir / "encyclopedia" / "entries.json"
        if enc.is_file() and "wikipedia" not in links and "wikidata" not in links:
            links = tuple(list(links) + ["wikipedia"])

    max_terms = opts.effective_kg_max_terms()
    print(
        f"[pipeline] {stage}: kg links={','.join(links)} "
        f"min_paper_count={opts.kg_min_paper_count} max_terms={max_terms} "
        f"document_limit={opts.document_limit} max_island={opts.kg_max_island}"
    )
    summary = build_kg(
        opts.workdir,
        kg_links=links,
        max_island=int(opts.kg_max_island),
        min_paper_count=int(opts.kg_min_paper_count),
        max_terms=int(max_terms),
        document_limit=opts.document_limit,
        write_html=True,
        open_browser=bool(opts.kg_open),
    )
    counts = summary.get("counts") or {}
    print(
        f"[pipeline] {stage}: kg nodes={counts.get('nodes')} "
        f"edges={counts.get('edges')} terms={counts.get('terms')} "
        f"islands={counts.get('islands')} html={summary.get('html_path')}"
    )
    summary = dict(summary)
    summary["kg_stage"] = stage
    return summary


def run_clusters() -> Dict[str, Any]:
    if use_placeholders():
        summary = run_placeholder("clusters")
        kg = _emit_display_kg("clusters")
        if kg:
            summary = dict(summary)
            summary["kg"] = kg
        return summary

    from semantic_corpus.cluster_review.step3 import build_clusters

    opts = options_from_env()
    print(
        f"[pipeline] clusters: algorithm={opts.cluster_algorithm} "
        f"resolution={opts.cluster_resolution}"
    )
    summary = build_clusters(
        opts.workdir,
        algorithm=opts.cluster_algorithm,
        resolution=float(opts.cluster_resolution),
    )
    kg = _emit_display_kg("clusters")
    extra: Dict[str, Any] = {
        "cluster_count": summary.get("cluster_count"),
        "paper_count": summary.get("paper_count"),
        "graph_summary": str(opts.workdir / "clusters" / "graph_summary.json"),
        "write_kg": bool(opts.write_kg),
    }
    if kg and kg.get("html_path"):
        extra["kg_html"] = kg.get("html_path")
        extra["kg_graph"] = kg.get("graph_path")
    _stamp("clusters", extra)
    print(f"[pipeline] clusters: {summary.get('cluster_count')} clusters")
    summary = dict(summary)
    if kg:
        summary["kg"] = kg
    return summary


def run_clean() -> Dict[str, Any]:
    return run_placeholder("clean")


def run_encyclopedia() -> Dict[str, Any]:
    if use_placeholders():
        summary = run_placeholder("encyclopedia")
        kg = _emit_display_kg("encyclopedia")
        if kg:
            summary = dict(summary)
            summary["kg"] = kg
        return summary

    from semantic_corpus.cluster_review.encyclopedia import build_encyclopedia

    opts = options_from_env()
    phrase_limit = opts.effective_phrase_limit()
    print(
        f"[pipeline] encyclopedia: lang={opts.encyclopedia_lang} "
        f"phrase_limit={phrase_limit} min_score={opts.min_score} "
        f"min_paper_count={opts.min_paper_count} "
        f"document_limit={opts.document_limit} from={opts.encyclopedia_source}"
    )
    summary = build_encyclopedia(
        opts.workdir,
        lang=opts.encyclopedia_lang,
        max_entries=int(phrase_limit),
        min_score=float(opts.min_score),
        min_paper_count=int(opts.min_paper_count),
        source=opts.encyclopedia_source,
        document_limit=opts.document_limit,
        force=False,
        write_html=True,
        fetch_html_descriptions=True,
    )
    kg = _emit_display_kg("encyclopedia")
    counts = summary.get("counts") or {}
    extra = {
        "entries_path": summary.get("entries_path"),
        "html_path": summary.get("html_path"),
        "selected": counts.get("selected"),
        "resolved": counts.get("resolved"),
        "ambiguous": counts.get("ambiguous"),
        "missing": counts.get("missing"),
        "error": counts.get("error"),
        "disambiguated": counts.get("disambiguated"),
        "phrase_source": (summary.get("params") or {}).get("phrase_source"),
        "write_kg": bool(opts.write_kg),
    }
    if kg and kg.get("html_path"):
        extra["kg_html"] = kg.get("html_path")
        extra["kg_graph"] = kg.get("graph_path")
    _stamp("encyclopedia", extra)
    html_note = f" html={summary.get('html_path')}" if summary.get("html_path") else ""
    print(
        f"[pipeline] encyclopedia: selected={counts.get('selected')} "
        f"resolved={counts.get('resolved')} missing={counts.get('missing')} "
        f"disambiguated={counts.get('disambiguated')} "
        f"error={counts.get('error')}{html_note}"
    )
    summary = dict(summary)
    if kg:
        summary["kg"] = kg
    return summary


STEP_ACTIONS = {
    "search": run_search,
    "collect": run_collect,
    "corpus": run_corpus,
    "phrases": run_phrases,
    "pdfs": run_pdfs,
    "clusters": run_clusters,
    "clean": run_clean,
    "encyclopedia": run_encyclopedia,
}


def run_step(step: str):
    """Run one pipeline step; map expected user errors to a clean doit failure."""
    action = STEP_ACTIONS.get(step)
    if action is None:
        raise KeyError(f"No action for step {step!r}")
    try:
        return action()
    except Exception as exc:
        # Avoid Python tracebacks for known user-facing failures (e.g. EPMC down).
        from semantic_corpus.core.exceptions import CorpusError, SemanticCorpusError

        if isinstance(exc, (CorpusError, SemanticCorpusError)):
            try:
                from doit.exceptions import TaskFailed
            except ImportError:
                raise exc
            return TaskFailed(str(exc))
        raise


def is_step_current(step: str) -> bool:
    """Uptodate: stamp exists; real mode also requires key artifacts."""
    opts = options_from_env()
    workdir = opts.workdir
    if not stamp_path(step, workdir).is_file():
        return False
    if use_placeholders():
        return True
    if step == "search":
        from semantic_corpus.pipeline.flat_corpus import path_search_results

        path = path_search_results(workdir)
        return path.is_file() and path.stat().st_size > 2
    if step == "collect":
        from semantic_corpus.pipeline.flat_corpus import (
            is_flat_corpus,
            list_paper_ids_from_search,
            paper_collect_done,
        )

        if not is_flat_corpus(workdir):
            return False
        ids = list_paper_ids_from_search(workdir)
        if not ids:
            return False
        # All hit-list papers must be collect-done (JSON + XML or recorded miss)
        return all(paper_collect_done(workdir, pid) for pid in ids)
    if step == "corpus":
        from semantic_corpus.cluster_review.packets import packet_index_is_current
        from semantic_corpus.pipeline.flat_corpus import is_bagit_or_packets_corpus

        return is_bagit_or_packets_corpus(workdir) and packet_index_is_current(
            workdir
        )
    if step == "phrases":
        from semantic_corpus.cluster_review.step2 import phrases_dir_for_corpus

        return (phrases_dir_for_corpus(workdir) / "index.json").is_file()
    if step == "pdfs":
        from semantic_corpus.pipeline.flat_corpus import (
            find_pdf,
            list_flat_paper_ids,
            list_paper_ids_from_search,
        )

        only = os.environ.get("PIPELINE_PAPER_ID", "").strip()
        ids = (
            [only]
            if only
            else (list_paper_ids_from_search(workdir) or list_flat_paper_ids(workdir))
        )
        if not ids:
            return False
        return all(find_pdf(workdir, pid) is not None for pid in ids)
    if step == "encyclopedia":
        from semantic_corpus.cluster_review.encyclopedia import encyclopedia_is_current

        return encyclopedia_is_current(
            workdir,
            lang=opts.encyclopedia_lang,
            max_entries=int(opts.effective_phrase_limit()),
            min_score=float(opts.min_score),
            min_paper_count=int(opts.min_paper_count),
            source=opts.encyclopedia_source,
            document_limit=opts.document_limit,
        )
    if step == "clusters":
        from semantic_corpus.pipeline.flat_corpus import indexes_dir

        legacy = workdir / "clusters" / "graph_summary.json"
        indexed = indexes_dir(workdir) / "clusters" / "graph_summary.json"
        return legacy.is_file() or indexed.is_file()
    return True
