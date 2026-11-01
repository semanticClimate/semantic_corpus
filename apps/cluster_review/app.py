"""Cluster-review Streamlit app — Steps 0–2 enabled; later stages locked.

Run:
  streamlit run apps/cluster_review/app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from semantic_corpus.cluster_review import (
    DEFAULT_METHOD,
    DEFAULT_N,
    build_clusters,
    clear_all_caches,
    create_corpus_from_query,
    extract_phrases,
    find_phrase_cache,
    list_demo_corpora,
    load_bagit_corpus,
    load_clusters,
    load_graph_summary,
    load_orphans,
    load_phrase_index,
)
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.utils import get_project_temp_dir

STAGES = [
    ("0", "Query → BAGIT"),
    ("1", "Load BAGIT"),
    ("2", "Phrases (TF-IDF)"),
    ("3", "Clusters"),
    ("4", "Remove clusters"),
    ("5", "Orphans"),
    ("6", "Summary"),
]

IMPLEMENTED = {"0", "1", "2", "3"}


def _init_state() -> None:
    if "active_stage" not in st.session_state:
        st.session_state.active_stage = "0"
    if "step0_summary" not in st.session_state:
        st.session_state.step0_summary = None
    if "step1_summary" not in st.session_state:
        st.session_state.step1_summary = None
    if "step2_summary" not in st.session_state:
        st.session_state.step2_summary = None
    if "step3_summary" not in st.session_state:
        st.session_state.step3_summary = None
    if "active_corpus" not in st.session_state:
        st.session_state.active_corpus = None


def _active_summary():
    return st.session_state.active_corpus


def _corpus_dir_from_active() -> Path | None:
    active = _active_summary()
    if not active:
        return None
    path = active.get("corpus_dir") or active.get("bag_root")
    return Path(path) if path else None


def main() -> None:
    st.set_page_config(page_title="Cluster review", layout="wide")
    _init_state()

    st.title("Cluster review — semantic_corpus")
    st.caption(
        "Steps 0–3: create/load a BAGIT, extract phrases, then view bipartite clusters. "
        "Later stages (remove / orphans / export) are locked until built."
    )

    with st.sidebar:
        st.header("Stages")
        for key, label in STAGES:
            disabled = key not in IMPLEMENTED
            if st.button(
                f"{'✓' if key in IMPLEMENTED else '🔒'} {key}. {label}",
                key=f"nav_{key}",
                disabled=disabled,
                use_container_width=True,
            ):
                st.session_state.active_stage = key
        st.divider()
        active = _active_summary()
        if active:
            st.metric(
                "Active papers",
                active.get("paper_count") or active.get("result_count") or 0,
            )
            st.caption(active.get("corpus_dir") or active.get("bag_root") or "")
            st.caption(f"Source step: {active.get('step')}")
        step2 = st.session_state.step2_summary
        if step2:
            st.metric("Unique phrases", step2.get("unique_phrases") or 0)
        step3 = st.session_state.step3_summary
        if step3:
            st.metric("Clusters", step3.get("cluster_count") or 0)

    stage = st.session_state.active_stage
    if stage == "0":
        _render_step0()
    elif stage == "1":
        _render_step1()
    elif stage == "2":
        _render_step2()
    elif stage == "3":
        _render_step3()
    else:
        st.info("This stage is not implemented yet.")


def _render_step0() -> None:
    st.subheader("Step 0 — Query → download → optional BAGIT")

    repos = RepositoryFactory.list_repositories()
    col1, col2 = st.columns(2)
    with col1:
        selected_repos = st.multiselect(
            "Repositories",
            options=repos,
            default=["europe_pmc"],
        )
        query_name = st.text_input("Query name", value="cluster_step0_demo")
        limit = st.number_input("Limit", min_value=1, max_value=50, value=3)
        formats = st.multiselect("Formats", ["xml", "pdf"], default=["xml"])
    with col2:
        query_string = st.text_area(
            "Query string",
            value='("marine heatwave") AND OPEN_ACCESS:Y AND HAS_FT:Y',
            height=120,
        )
        create_bagit = st.checkbox("Create BAGIT corpus", value=True)
        query_dir = st.text_input(
            "Query / download directory",
            value=str(Path(get_project_temp_dir(), "queries", query_name or "demo")),
        )
        corpus_dir = st.text_input(
            "BAGIT corpus directory",
            value=str(Path("corpora", query_name or "demo")),
        )

    if st.button("Run Step 0", type="primary"):
        if not selected_repos:
            st.error("Select at least one repository.")
            return
        if not query_string.strip():
            st.error("Query string is required.")
            return
        with st.spinner("Searching and downloading…"):
            try:
                summary = create_corpus_from_query(
                    query_string=query_string.strip(),
                    query_name=query_name.strip() or "cluster_step0_demo",
                    query_dir=Path(query_dir),
                    repositories=selected_repos,
                    limit=int(limit),
                    formats=formats or ["xml"],
                    corpus_dir=Path(corpus_dir) if create_bagit else None,
                    create_bagit=create_bagit,
                )
            except Exception as exc:
                st.exception(exc)
                return
        st.session_state.step0_summary = summary
        if create_bagit:
            st.session_state.active_corpus = summary
        st.success(
            f"Done: {summary['result_count']} results, "
            f"{summary['downloaded_count']} downloaded, "
            f"{summary['bagit_paper_count']} in BAGIT."
        )

    summary = st.session_state.step0_summary
    if not summary:
        st.info("Configure the query and click **Run Step 0**.")
        return

    st.write("### Summary")
    st.json({k: v for k, v in summary.items() if k != "rows"})
    rows = summary.get("rows") or []
    if rows:
        st.write("### Review rows (preview)")
        st.dataframe(
            [
                {
                    "paper_id": r.get("paper_id"),
                    "title": (r.get("title") or "")[:120],
                    "review_status": r.get("review_status"),
                    "has_xml": r.get("has_xml"),
                }
                for r in rows
            ],
            use_container_width=True,
        )


def _render_step1() -> None:
    st.subheader("Step 1 — Load existing BAGIT corpus")

    demos = list_demo_corpora()
    demo_names = ["(choose path below)"] + sorted(demos.keys())
    choice = st.selectbox("Demo corpus", demo_names)
    corpus_path = st.text_input(
        "BAGIT corpus path",
        value="" if choice.startswith("(") else str(demos[choice]),
    )
    query_name = st.text_input("Query name (for review table provenance)", value="")
    query_string = st.text_input("Query string (optional)", value="")

    if st.button("Load BAGIT", type="primary"):
        path = Path(corpus_path.strip())
        if not corpus_path.strip():
            st.error("Provide a corpus path or choose a demo.")
            return
        with st.spinner("Loading BAGIT…"):
            try:
                summary = load_bagit_corpus(
                    path,
                    query_name=query_name.strip(),
                    query_string=query_string.strip(),
                )
            except Exception as exc:
                st.exception(exc)
                return
        st.session_state.step1_summary = summary
        st.session_state.active_corpus = summary
        st.success(f"Loaded {summary['paper_count']} papers from {summary['bag_root']}")

    summary = st.session_state.step1_summary
    if not summary:
        st.info("Choose a demo or path and click **Load BAGIT**.")
        if demos:
            st.caption("Available demos: " + ", ".join(sorted(demos)))
        return

    st.write("### Summary")
    st.json({k: v for k, v in summary.items() if k not in ("rows", "papers", "paper_ids")})

    papers = summary.get("papers") or []
    if papers:
        st.write("### Papers")
        st.dataframe(papers, use_container_width=True)


def _render_step2() -> None:
    st.subheader("Step 2 — Phrases (YAKE, n=3)")

    corpus_dir = _corpus_dir_from_active()
    demos = list_demo_corpora()
    if corpus_dir is None:
        st.warning("No active corpus. Load one in Step 1 (or create in Step 0), or pick a path below.")
        demo_names = ["(choose path below)"] + sorted(demos.keys())
        choice = st.selectbox("Demo corpus", demo_names, key="step2_demo")
        corpus_path = st.text_input(
            "BAGIT corpus path",
            value="" if choice.startswith("(") else str(demos[choice]),
            key="step2_path",
        )
        if corpus_path.strip():
            corpus_dir = Path(corpus_path.strip())
    else:
        st.info(f"Active corpus: `{corpus_dir}`")
        override = st.text_input("Or override corpus path", value=str(corpus_dir), key="step2_override")
        corpus_dir = Path(override.strip()) if override.strip() else corpus_dir

    col1, col2, col3 = st.columns(3)
    with col1:
        n = st.number_input("Max n-gram", min_value=1, max_value=5, value=DEFAULT_N)
    with col2:
        top = st.number_input("Top phrases / paper", min_value=1, max_value=50, value=15)
    with col3:
        force = st.checkbox("Force re-extract (ignore cache)", value=False)
    method = st.selectbox(
        "Phrase method",
        options=["tfidf", "yake"],
        index=0 if DEFAULT_METHOD == "tfidf" else 1,
        help="TF-IDF (default): corpus-relative, fast. YAKE: per-paper fallback.",
    )
    st.caption(
        "Indexes **XML body only** — front matter (title/abstract) and "
        "references / acknowledgments sections are excluded."
    )
    include_front_matter = st.checkbox(
        "Also include title + abstract",
        value=False,
        help="Off by default. Body text still skips References / Acknowledgments.",
    )
    include_xml_body = True

    if corpus_dir and corpus_dir.exists():
        try:
            bag = load_bagit_corpus(corpus_dir, write_review_if_missing=False)
            cache_status = find_phrase_cache(corpus_dir, bag.get("paper_ids") or [])
            st.caption(
                f"Cache: {cache_status['cached_count']} ready, "
                f"{cache_status['missing_count']} missing "
                f"({cache_status['phrases_dir']})"
            )
        except Exception:
            cache_status = None
            bag = None
    else:
        cache_status = None
        bag = None

    run_col, load_col, clear_col = st.columns(3)
    with run_col:
        run = st.button("Extract phrases", type="primary")
    with load_col:
        load_cached = st.button("Use cached phrases")
    with clear_col:
        clear_caches = st.button("Clear all caches")

    if clear_caches:
        if corpus_dir is None or not str(corpus_dir).strip():
            st.error("Provide a corpus path.")
            return
        try:
            cleared = clear_all_caches(corpus_dir)
        except Exception as exc:
            st.exception(exc)
            return
        st.session_state.step2_summary = None
        st.success(
            f"Cleared {cleared['deleted_count']} cache file(s) under "
            f"`{cleared['phrases_dir']}`."
        )
        if cleared.get("errors"):
            st.warning("Some deletions failed: " + "; ".join(cleared["errors"]))
        st.rerun()

    if run or load_cached:
        if corpus_dir is None or not str(corpus_dir).strip():
            st.error("Provide a corpus path.")
            return
        if load_cached and not force:
            index = load_phrase_index(corpus_dir)
            if index and index.get("paper_count"):
                # Reload full records from per-paper files
                with st.spinner("Loading phrase cache…"):
                    summary = extract_phrases(
                        corpus_dir,
                        method=method,
                        n=int(n),
                        top=int(top),
                        use_cache=True,
                        force=False,
                        include_xml_body=include_xml_body,
                        include_front_matter=include_front_matter,
                    )
                st.session_state.step2_summary = summary
                st.session_state.active_corpus = {
                    **(_active_summary() or {}),
                    "corpus_dir": summary["corpus_dir"],
                    "bag_root": summary["bag_root"],
                    "paper_count": summary["paper_count"],
                    "step": 2,
                    "phrases_dir": summary["phrases_dir"],
                }
                st.success(
                    f"Loaded cache: {summary['papers_from_cache']} papers, "
                    f"{summary['unique_phrases']} unique phrases."
                )
            else:
                st.warning("No phrase cache found — run Extract YAKE first.")
                return
        else:
            progress = st.progress(0.0, text="Extracting…")
            status = st.empty()

            def _cb(i: int, total: int, paper_id: str, elapsed: float) -> None:
                progress.progress(i / total, text=f"{i}/{total} {paper_id}")
                status.caption(f"Last: {paper_id} ({elapsed:.2f}s)")

            with st.spinner(f"Running {method}…"):
                try:
                    summary = extract_phrases(
                        corpus_dir,
                        method=method,
                        n=int(n),
                        top=int(top),
                        use_cache=not force,
                        force=force,
                        progress_callback=_cb,
                        include_xml_body=include_xml_body,
                        include_front_matter=include_front_matter,
                    )
                except Exception as exc:
                    st.exception(exc)
                    return
            progress.progress(1.0, text="Done")
            st.session_state.step2_summary = summary
            st.session_state.active_corpus = {
                **(_active_summary() or {}),
                "corpus_dir": summary["corpus_dir"],
                "bag_root": summary["bag_root"],
                "paper_count": summary["paper_count"],
                "step": 2,
                "phrases_dir": summary["phrases_dir"],
            }
            st.success(
                f"Done in {summary['elapsed_s']}s: "
                f"{summary['papers_extracted']} extracted, "
                f"{summary['papers_from_cache']} from cache, "
                f"{summary['unique_phrases']} unique phrases."
            )

    summary = st.session_state.step2_summary
    if not summary:
        st.info("Extract YAKE phrases (or load cache) for the active corpus.")
        return

    st.write("### Summary")
    st.json(
        {
            k: v
            for k, v in summary.items()
            if k not in ("papers", "paper_ids")
        }
    )

    papers = summary.get("papers") or []
    if not papers:
        return

    st.write("### Per-paper phrases")
    ids = [p["paper_id"] for p in papers]
    selected = st.selectbox("Paper", ids)
    paper = next(p for p in papers if p["paper_id"] == selected)
    st.caption(
        f"{paper['phrase_count']} phrases · source={paper['source']} · "
        f"text={paper.get('text_source')}"
    )
    phrase_rows = paper.get("phrases") or []
    if phrase_rows:
        st.dataframe(phrase_rows, use_container_width=True)
    else:
        st.warning("No phrases for this paper (empty title/abstract?).")

    st.write("### Corpus phrase counts")
    st.dataframe(
        [
            {
                "paper_id": p["paper_id"],
                "phrase_count": p["phrase_count"],
                "source": p["source"],
            }
            for p in papers
        ],
        use_container_width=True,
    )


def _render_step3() -> None:
    st.subheader("Step 3 — Bipartite clusters (read-only)")

    corpus_dir = _corpus_dir_from_active()
    demos = list_demo_corpora()
    demo_names = ["(choose demo)"] + sorted(demos.keys())

    if corpus_dir is None:
        choice = st.selectbox("Demo corpus", demo_names, key="step3_demo")
        corpus_path = st.text_input(
            "BAGIT corpus path",
            value="" if choice.startswith("(") else str(demos[choice]),
            key="step3_path",
        )
        if corpus_path.strip():
            corpus_dir = Path(corpus_path.strip())
    else:
        st.info(f"Active corpus: `{corpus_dir}`")
        override = st.text_input(
            "Or override corpus path", value=str(corpus_dir), key="step3_override"
        )
        corpus_dir = Path(override.strip()) if override.strip() else corpus_dir

    col1, col2, col3 = st.columns(3)
    with col1:
        algorithm = st.selectbox("Algorithm", ["louvain", "greedy"], index=0)
    with col2:
        resolution = st.number_input(
            "Resolution", min_value=0.1, max_value=5.0, value=1.0, step=0.1
        )
    with col3:
        min_papers = st.number_input(
            "Min papers / cluster", min_value=1, max_value=20, value=2
        )

    run_col, load_col = st.columns(2)
    with run_col:
        run = st.button("Build clusters", type="primary")
    with load_col:
        load_cached = st.button("Load existing clusters")

    if run or load_cached:
        if corpus_dir is None or not str(corpus_dir).strip():
            st.error("Provide a corpus path.")
            return
        try:
            if load_cached and not run:
                loaded = load_clusters(corpus_dir)
                orphans = load_orphans(corpus_dir)
                graph = load_graph_summary(corpus_dir)
                if not loaded or not graph:
                    st.warning("No clusters cache — run Build clusters first.")
                    return
                summary = {
                    **graph,
                    "clusters": loaded.get("clusters") or [],
                    "orphans": orphans or {"paper_ids": [], "terms": []},
                }
            else:
                with st.spinner("Building bipartite clusters…"):
                    summary = build_clusters(
                        corpus_dir,
                        algorithm=algorithm,
                        resolution=float(resolution),
                        min_cluster_papers=int(min_papers),
                    )
            st.session_state.step3_summary = summary
            st.session_state.active_corpus = {
                **(_active_summary() or {}),
                "corpus_dir": summary["corpus_dir"],
                "paper_count": summary.get("paper_count"),
                "step": 3,
                "clusters_dir": summary.get("clusters_dir"),
            }
            st.success(
                f"{summary.get('cluster_count')} clusters · "
                f"{summary.get('orphan_paper_count')} orphan papers · "
                f"{summary.get('edge_count')} edges"
            )
        except Exception as exc:
            st.exception(exc)
            return

    summary = st.session_state.step3_summary
    if not summary:
        # Try auto-load from disk
        if corpus_dir and Path(corpus_dir, "clusters", "clusters.json").is_file():
            summary = {
                **(load_graph_summary(corpus_dir) or {}),
                "clusters": (load_clusters(corpus_dir) or {}).get("clusters") or [],
                "orphans": load_orphans(corpus_dir) or {},
            }
            st.session_state.step3_summary = summary
        else:
            st.info("Build clusters from Step 2 phrases for the active corpus.")
            return

    st.write("### Graph summary")
    st.json(
        {
            k: v
            for k, v in summary.items()
            if k not in ("clusters", "orphans")
        }
    )

    clusters = summary.get("clusters") or []
    st.write(f"### Clusters ({len(clusters)})")
    for cluster in clusters:
        with st.expander(
            f"[{cluster.get('cluster_id')}] {cluster.get('theme', '')[:100]} "
            f"({cluster.get('paper_count')} papers)",
            expanded=False,
        ):
            st.write("**Papers**")
            st.write(", ".join(cluster.get("paper_ids") or []))
            st.write("**Top terms**")
            st.dataframe(
                (cluster.get("terms") or [])[:15],
                use_container_width=True,
            )

    orphans = summary.get("orphans") or {}
    st.write("### Orphans (read-only)")
    st.caption(
        f"{orphans.get('paper_count') or len(orphans.get('paper_ids') or [])} papers · "
        f"{orphans.get('term_count') or len(orphans.get('terms') or [])} terms"
    )
    if orphans.get("paper_ids"):
        st.write(", ".join(orphans["paper_ids"]))


if __name__ == "__main__":
    main()
