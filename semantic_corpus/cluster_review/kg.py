"""Knowledge graph assembly + HTML display (post-clusters).

v1 edges come from cluster BKG membership (bipartite paper↔term). Optional
encyclopedia links are used to merge synonym terms, then dropped so the
displayed graph stays bipartite. Writes under ``<workdir>/kg/``.
"""

from __future__ import annotations

import json
import webbrowser
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from semantic_corpus.core.exceptions import CorpusError

DEFAULT_KG_LINKS = ("clusters",)
DEFAULT_MAX_ISLAND = 20
DEFAULT_KG_MAX_TERMS = 40
DEFAULT_KG_MIN_PAPER_COUNT = 2


def kg_dir(workdir: Path) -> Path:
    return Path(workdir) / "kg"


def graph_path(workdir: Path) -> Path:
    return kg_dir(workdir) / "graph.json"


def islands_path(workdir: Path) -> Path:
    return kg_dir(workdir) / "islands.json"


def summary_path(workdir: Path) -> Path:
    return kg_dir(workdir) / "kg_summary.json"


def html_path(workdir: Path) -> Path:
    return kg_dir(workdir) / "knowledge_graph.html"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _node(
    node_id: str,
    *,
    label: str,
    kind: str,
    group: str,
    title: str = "",
    value: float = 10.0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "id": node_id,
        "label": label,
        "kind": kind,
        "group": group,
        "title": title or label,
        "value": float(value),
    }
    if extra:
        row.update(extra)
    return row


def _edge(
    source: str,
    target: str,
    *,
    weight: float = 1.0,
    link_source: str,
    title: str = "",
) -> Dict[str, Any]:
    a, b = sorted([source, target])
    return {
        "id": f"{link_source}:{a}::{b}",
        "from": a,
        "to": b,
        "source": a,
        "target": b,
        "weight": float(weight),
        "value": float(weight),
        "link_source": link_source,
        "title": title or f"{link_source} ({weight:g})",
    }


def select_kg_terms(
    workdir: Path,
    *,
    min_paper_count: int = DEFAULT_KG_MIN_PAPER_COUNT,
    max_terms: int = DEFAULT_KG_MAX_TERMS,
) -> Tuple[Set[str], Dict[str, int], str]:
    """Pick retained phrases for the KG via ``n_papers`` + max-terms cap.

    Prefers ``phrases/phrases_terms.csv``. Falls back to paper membership
    counts inferred from ``clusters/clusters.json``.

    Returns ``(allowed_phrases, n_papers_map, source_label)``.
    """
    if min_paper_count < 1:
        raise CorpusError("min_paper_count must be >= 1")
    if max_terms < 1:
        raise CorpusError("max_terms must be >= 1")

    workdir = Path(workdir)
    # Reuse encyclopedia phrase ranking (phrases_terms path) when available.
    from semantic_corpus.cluster_review.encyclopedia import (
        _scores_from_phrases_terms,
    )

    scores, _displays, n_papers_map = _scores_from_phrases_terms(
        workdir, demoted=set(), min_paper_count=int(min_paper_count)
    )
    source = "phrases_terms"
    if not scores:
        # Fallback: count distinct papers per term from clusters.
        doc = _load_json(workdir / "clusters" / "clusters.json") or {}
        paper_sets: Dict[str, Set[str]] = defaultdict(set)
        weight_map: Dict[str, float] = defaultdict(float)
        for cluster in doc.get("clusters") or []:
            papers = [str(p) for p in (cluster.get("paper_ids") or []) if p]
            for term in cluster.get("terms") or []:
                if not isinstance(term, dict):
                    continue
                phrase = str(term.get("phrase") or "").strip().lower()
                if not phrase:
                    continue
                paper_sets[phrase].update(papers)
                weight_map[phrase] += float(term.get("weight") or 0.0)
        n_papers_map = {p: len(s) for p, s in paper_sets.items()}
        scores = {
            p: float(n_papers_map[p]) * 1000.0 + weight_map.get(p, 0.0)
            for p in n_papers_map
            if n_papers_map[p] >= int(min_paper_count)
        }
        source = "clusters"

    ranked = sorted(
        scores.keys(),
        key=lambda p: (-int(n_papers_map.get(p, 0)), -float(scores.get(p, 0)), p),
    )[: int(max_terms)]
    allowed = set(ranked)
    kept_papers = {p: int(n_papers_map.get(p, 0)) for p in allowed}
    return allowed, kept_papers, source


def load_paper_titles(workdir: Path) -> Dict[str, str]:
    """Map ``paper_id`` → title from review table and/or ``data/metadata``."""
    workdir = Path(workdir)
    titles: Dict[str, str] = {}

    review_path = workdir / "review" / "review_table.json"
    review = _load_json(review_path)
    rows: List[Any] = []
    if isinstance(review, list):
        rows = review
    elif isinstance(review, dict):
        maybe = review.get("rows") or review.get("papers") or []
        if isinstance(maybe, list):
            rows = maybe
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("paper_id") or row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        if pid and title:
            titles[pid] = title

    meta_dir = workdir / "data" / "metadata"
    if meta_dir.is_dir():
        for path in meta_dir.glob("*_metadata.json"):
            pid = path.name[: -len("_metadata.json")]
            if pid in titles:
                continue
            doc = _load_json(path) or {}
            title = str(doc.get("title") or "").strip()
            if title:
                titles[pid] = title
    return titles


def links_from_clusters(
    workdir: Path,
    *,
    allowed_phrases: Optional[Set[str]] = None,
    allowed_papers: Optional[Set[str]] = None,
    n_papers_map: Optional[Dict[str, int]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Bipartite paper↔term edges from ``clusters/clusters.json``.

    When ``allowed_phrases`` is set, only those terms are kept (and papers with
    no remaining term edges are dropped). ``allowed_papers`` caps which
    document nodes appear (``--document-limit``).
    """
    workdir = Path(workdir)
    doc = _load_json(workdir / "clusters" / "clusters.json")
    if not doc or not isinstance(doc.get("clusters"), list):
        raise CorpusError(
            f"Missing clusters/clusters.json under {workdir}; run clusters first"
        )

    paper_titles = load_paper_titles(workdir)
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[str, Dict[str, Any]] = {}
    paper_has_term: Set[str] = set()

    for cluster in doc["clusters"]:
        cid = cluster.get("cluster_id")
        papers = [str(p) for p in (cluster.get("paper_ids") or []) if p]
        if allowed_papers is not None:
            papers = [p for p in papers if p in allowed_papers]
            if not papers:
                continue
        terms = [
            t
            for t in (cluster.get("terms") or [])
            if isinstance(t, dict) and t.get("phrase")
        ]
        for term in terms:
            phrase = str(term.get("phrase") or "").strip().lower()
            if not phrase:
                continue
            if allowed_phrases is not None and phrase not in allowed_phrases:
                continue
            tid = f"term:{phrase}"
            weight = float(term.get("weight") or 1.0)
            disp = str(term.get("display") or phrase)
            n_papers = int((n_papers_map or {}).get(phrase, 0))
            title_bits = [f"cluster weight {weight:g}"]
            if n_papers:
                title_bits.append(f"n_papers {n_papers}")
            prev = nodes.get(tid)
            if prev is None:
                nodes[tid] = _node(
                    tid,
                    label=disp,
                    kind="term",
                    group="Term",
                    title=f"{disp} ({'; '.join(title_bits)})",
                    value=8.0 + min(weight, 20.0),
                    extra={
                        "phrase": phrase,
                        "cluster_id": cid,
                        "n_papers": n_papers or None,
                    },
                )
            else:
                prev["value"] = max(
                    float(prev.get("value") or 0), 8.0 + min(weight, 20.0)
                )

            for pid in papers:
                nid = f"paper:{pid}"
                if nid not in nodes:
                    short = pid.replace("europe_pmc_", "")
                    paper_title = paper_titles.get(pid) or ""
                    tip = (
                        f"{paper_title}\n({short})"
                        if paper_title
                        else f"Paper {pid}"
                    )
                    nodes[nid] = _node(
                        nid,
                        label=short,
                        kind="paper",
                        group="Paper",
                        title=tip,
                        value=12.0,
                        extra={
                            "paper_id": pid,
                            "cluster_id": cid,
                            "paper_title": paper_title or None,
                        },
                    )
                paper_has_term.add(nid)
                eid = _edge(
                    nid,
                    tid,
                    weight=weight,
                    link_source="clusters",
                    title=f"cluster {cid}: paper↔{disp}",
                )
                edges[eid["id"]] = eid

    if allowed_phrases is not None:
        # Drop papers that lost all term links after filtering.
        nodes = {
            nid: node
            for nid, node in nodes.items()
            if node.get("kind") != "paper" or nid in paper_has_term
        }
        node_ids = set(nodes)
        edges = {
            eid: edge
            for eid, edge in edges.items()
            if edge["from"] in node_ids and edge["to"] in node_ids
        }

    return list(nodes.values()), list(edges.values())


def links_from_encyclopedia(
    workdir: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Attach resolved encyclopedia entities to matching term nodes."""
    from semantic_corpus.cluster_review.encyclopedia import load_entries

    doc = load_entries(workdir)
    if not doc:
        return [], []

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    for entry in doc.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") not in {"resolved", "ambiguous"}:
            continue
        phrase = str(entry.get("phrase") or "").strip().lower()
        title = str(entry.get("wiki_title") or entry.get("display") or phrase)
        if not phrase or not title:
            continue
        wid = entry.get("wikidata_id") or ""
        eid = f"wiki:{wid}" if wid else f"wiki:{title.lower()}"
        nodes.append(
            _node(
                eid,
                label=title,
                kind="encyclopedia",
                group="Encyclopedia",
                title=(
                    f"<b>{title}</b><br>"
                    f"Wikidata: {wid or '—'}<br>"
                    f"{entry.get('wiki_url') or ''}"
                ),
                value=18.0,
                extra={
                    "wikidata_id": wid,
                    "wiki_url": entry.get("wiki_url"),
                    "phrase": phrase,
                    "wiki_title": title,
                },
            )
        )
        edges.append(
            _edge(
                f"term:{phrase}",
                eid,
                weight=2.0,
                link_source="wikipedia",
                title=f"encyclopedia resolve: {phrase} → {title}",
            )
        )
    return nodes, edges


def _term_merge_key(node: Dict[str, Any]) -> Tuple[int, float, int, str]:
    """Prefer higher n_papers / weight, then longer label, then id."""
    n_papers = int(node.get("n_papers") or 0)
    value = float(node.get("value") or 0.0)
    label = str(node.get("label") or "")
    return (n_papers, value, len(label), str(node.get("id") or ""))


def collapse_encyclopedia_synonyms(
    nodes: Dict[str, Dict[str, Any]],
    edges: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Merge term synonyms linked through the same wiki entity; drop lone greens.

    ``blue1 — green — blue2`` means the two terms resolve to one encyclopedia
    page → collapse into a single blue term. Encyclopedia nodes with fewer than
    two retained term neighbours are removed (including former synonym bridges
    once merged).
    """
    wiki_to_terms: Dict[str, Set[str]] = defaultdict(set)
    for edge in edges.values():
        a = edge.get("from") or edge.get("source")
        b = edge.get("to") or edge.get("target")
        if not a or not b:
            continue
        if a.startswith("wiki:") and b.startswith("term:"):
            wiki_to_terms[a].add(b)
        elif b.startswith("wiki:") and a.startswith("term:"):
            wiki_to_terms[b].add(a)

    # Union-find over terms that share a multi-term wiki entity
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # Prefer richer term as root for stable ids
        na, nb = nodes.get(ra, {}), nodes.get(rb, {})
        if _term_merge_key(nb) > _term_merge_key(na):
            parent[ra] = rb
        else:
            parent[rb] = ra

    synonym_groups = 0
    multi_wiki_links: List[Tuple[str, List[str]]] = []
    for wiki_id, term_ids in wiki_to_terms.items():
        present = sorted(t for t in term_ids if t in nodes)
        if len(present) < 2:
            continue
        synonym_groups += 1
        multi_wiki_links.append((wiki_id, present))
        for tid in present[1:]:
            union(present[0], tid)

    wiki_for_group: Dict[str, str] = {}
    for wiki_id, present in multi_wiki_links:
        wiki_for_group[find(present[0])] = wiki_id

    # Collect synonym members per canonical term
    members_by_canon: Dict[str, List[str]] = defaultdict(list)
    for tid in list(parent):
        members_by_canon[find(tid)].append(tid)

    remap: Dict[str, str] = {}
    merged_into: Dict[str, List[str]] = defaultdict(list)
    for canon, members in members_by_canon.items():
        unique = sorted(set(members))
        if len(unique) < 2:
            continue
        for tid in unique:
            if tid == canon:
                continue
            remap[tid] = canon
            merged_into[canon].append(tid)

    # Enrich canonical term nodes with synonym metadata + wiki label preference
    for canon, aliases in merged_into.items():
        node = nodes.get(canon)
        if not node:
            continue
        alias_labels: List[str] = []
        for alias_id in aliases:
            alias = nodes.get(alias_id) or {}
            lab = str(alias.get("label") or alias.get("phrase") or "")
            if lab and lab != node.get("label"):
                alias_labels.append(lab)
            node["value"] = max(
                float(node.get("value") or 0), float(alias.get("value") or 0)
            )
            node["n_papers"] = max(
                int(node.get("n_papers") or 0), int(alias.get("n_papers") or 0)
            )
            orig = str(alias.get("phrase") or "")
            if orig and orig != node.get("phrase"):
                alias_labels.append(str(alias.get("label") or orig))

        wiki_id = wiki_for_group.get(canon)
        wiki_node = nodes.get(wiki_id or "") or {}
        wiki_title = wiki_node.get("wiki_title") or wiki_node.get("label")
        wiki_url = wiki_node.get("wiki_url")
        wid = wiki_node.get("wikidata_id")
        if wiki_title:
            node["label"] = str(wiki_title)
        synonyms = sorted(
            {
                *(alias_labels),
                str(node.get("phrase") or ""),
                *(
                    str((nodes.get(a) or {}).get("phrase") or "")
                    for a in aliases
                ),
            }
        )
        synonyms = [s for s in synonyms if s and s != node.get("label")]
        node["synonyms"] = synonyms
        tip = str(node.get("title") or node.get("label") or "")
        if synonyms:
            tip = f"{tip}<br>synonyms: {', '.join(synonyms)}"
        if wiki_title:
            tip = f"{tip}<br>Wikipedia: {wiki_title}"
        if wid:
            tip = f"{tip}<br>Wikidata: {wid}"
        if wiki_url:
            tip = f"{tip}<br>{wiki_url}"
        node["title"] = tip
        if wid:
            node["wikidata_id"] = wid
        if wiki_url:
            node["wiki_url"] = wiki_url

    # Drop merged alias term nodes
    for alias_id in remap:
        nodes.pop(alias_id, None)

    # Rewrite edges through remap; drop self-loops; re-key
    new_edges: Dict[str, Dict[str, Any]] = {}
    for edge in edges.values():
        a = edge.get("from") or edge.get("source")
        b = edge.get("to") or edge.get("target")
        if not a or not b:
            continue
        a2 = remap.get(a, a)
        b2 = remap.get(b, b)
        if a2 == b2:
            continue
        if a2 not in nodes or b2 not in nodes:
            continue
        rewritten = _edge(
            a2,
            b2,
            weight=float(edge.get("weight") or 1.0),
            link_source=str(edge.get("link_source") or "clusters"),
            title=str(edge.get("title") or ""),
        )
        prev = new_edges.get(rewritten["id"])
        if prev is None or float(rewritten["weight"]) > float(prev.get("weight") or 0):
            new_edges[rewritten["id"]] = rewritten

    # Drop 1-connected (and 0-connected) encyclopedia nodes
    wiki_deg: Dict[str, int] = defaultdict(int)
    for edge in new_edges.values():
        a, b = edge["from"], edge["to"]
        if a.startswith("wiki:"):
            wiki_deg[a] += 1
        if b.startswith("wiki:"):
            wiki_deg[b] += 1

    dropped_wiki = 0
    for nid, node in list(nodes.items()):
        if node.get("kind") != "encyclopedia":
            continue
        if wiki_deg.get(nid, 0) < 2:
            nodes.pop(nid, None)
            dropped_wiki += 1

    node_ids = set(nodes)
    new_edges = {
        eid: edge
        for eid, edge in new_edges.items()
        if edge["from"] in node_ids and edge["to"] in node_ids
    }

    stats = {
        "synonym_groups": synonym_groups,
        "terms_merged": len(remap),
        "encyclopedia_dropped": dropped_wiki,
        "synonym_map": {k: remap[k] for k in sorted(remap)},
    }
    return nodes, new_edges, stats


def detect_islands(
    nodes: Sequence[Dict[str, Any]],
    edges: Sequence[Dict[str, Any]],
    *,
    max_island: int = DEFAULT_MAX_ISLAND,
) -> List[Dict[str, Any]]:
    """Connected components (undirected) smaller than or equal to ``max_island``."""
    adj: Dict[str, Set[str]] = defaultdict(set)
    ids = {n["id"] for n in nodes}
    for e in edges:
        a, b = e.get("from") or e.get("source"), e.get("to") or e.get("target")
        if a in ids and b in ids:
            adj[a].add(b)
            adj[b].add(a)
    for nid in ids:
        adj.setdefault(nid, set())

    seen: Set[str] = set()
    islands: List[Dict[str, Any]] = []
    for nid in sorted(ids):
        if nid in seen:
            continue
        stack = [nid]
        comp: List[str] = []
        seen.add(nid)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if 1 <= len(comp) <= int(max_island):
            islands.append(
                {
                    "size": len(comp),
                    "node_ids": sorted(comp),
                    "kinds": sorted(
                        {
                            next(
                                (
                                    n.get("kind")
                                    for n in nodes
                                    if n["id"] == x
                                ),
                                "unknown",
                            )
                            for x in comp
                        }
                    ),
                }
            )
    islands.sort(key=lambda r: (-int(r["size"]), r["node_ids"][0] if r["node_ids"] else ""))
    return islands


def nodes_edges_to_vis(
    nodes: Sequence[Dict[str, Any]],
    edges: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convert KG graph.json nodes/edges to vis-network datasets."""
    vis_nodes = []
    for n in nodes:
        raw = str(n.get("title") or n.get("label") or n["id"])
        vis_nodes.append(
            {
                "id": n["id"],
                "label": n.get("label") or n["id"],
                # Custom field only — omit vis `title` to avoid a second popup
                "tooltip": raw.replace("\n", "<br>"),
                "value": n.get("value") or 10,
                "group": n.get("group") or n.get("kind") or "node",
            }
        )
    vis_edges = [
        {
            "from": e.get("from") or e.get("source"),
            "to": e.get("to") or e.get("target"),
            "value": e.get("value") or e.get("weight") or 1,
        }
        for e in edges
    ]
    return vis_nodes, vis_edges


def write_kg_html(
    nodes: Sequence[Dict[str, Any]],
    edges: Sequence[Dict[str, Any]],
    output: Path,
    *,
    title: str = "Knowledge graph",
    resolution: float = 1.0,
) -> Path:
    """Write vis-network HTML with Louvain resolution slider (needs ``pipeline kg --view``)."""
    vis_nodes, vis_edges = nodes_edges_to_vis(nodes, edges)
    payload = {
        "nodes": vis_nodes,
        "edges": vis_edges,
        "title": title,
        "resolution": float(resolution),
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f8fafc; color: #0f172a; }}
    header {{
      padding: 10px 16px 12px;
      border-bottom: 1px solid #e2e8f0;
      background: #fff;
      display: flex;
      flex-wrap: wrap;
      gap: 12px 24px;
      align-items: flex-end;
      justify-content: space-between;
    }}
    header .titles h1 {{ margin: 0; font-size: 1.1rem; font-weight: 600; }}
    header .titles p {{ margin: 4px 0 0; font-size: 0.85rem; color: #64748b; }}
    #controls {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: min(420px, 100%);
    }}
    #controls label {{
      font-size: 0.8rem;
      color: #334155;
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }}
    #controls input[type=range] {{ width: 100%; }}
    #status {{ font-size: 0.75rem; color: #64748b; min-height: 1.1em; }}
    #status.err {{ color: #b91c1c; }}
    #mynetwork {{ width: 100%; height: calc(100vh - 96px); position: relative; }}
    #tooltip {{
      display: none;
      position: fixed;
      z-index: 20;
      max-width: min(420px, 80vw);
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
      background: #0f172a;
      color: #f8fafc;
      font-size: 0.85rem;
      line-height: 1.35;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.25);
      pointer-events: none;
      white-space: normal;
    }}
    div.vis-tooltip {{ display: none !important; }}
  </style>
</head>
<body>
  <header>
    <div class="titles">
      <h1>{title}</h1>
      <p id="stats">{len(vis_nodes)} nodes · {len(vis_edges)} edges — drag, zoom, hover</p>
    </div>
    <div id="controls">
      <label>
        <span>Louvain resolution (lower = aggregate)</span>
        <span id="resValue">{resolution:g}</span>
      </label>
      <input id="resSlider" type="range" min="0.2" max="2.5" step="0.05" value="{resolution:g}"/>
      <div id="status">Open via <code>pipeline kg --view</code> for live rebuild</div>
    </div>
  </header>
  <div id="mynetwork"></div>
  <div id="tooltip"></div>
  <script>
    const payload = {json.dumps(payload, ensure_ascii=False)};
    const nodes = new vis.DataSet(payload.nodes);
    const edges = new vis.DataSet(payload.edges);
    const container = document.getElementById('mynetwork');
    const tip = document.getElementById('tooltip');
    const stats = document.getElementById('stats');
    const statusEl = document.getElementById('status');
    const slider = document.getElementById('resSlider');
    const resValue = document.getElementById('resValue');
    const apiEnabled = location.protocol === 'http:' || location.protocol === 'https:';

    const network = new vis.Network(
      container,
      {{ nodes, edges }},
      {{
        nodes: {{
          shape: 'dot',
          font: {{ size: 14, color: '#0f172a' }},
          borderWidth: 2,
          scaling: {{ min: 8, max: 36 }}
        }},
        edges: {{
          color: {{ color: '#94a3b8', highlight: '#2563eb' }},
          smooth: {{ type: 'continuous' }}
        }},
        groups: {{
          Paper: {{ color: {{ background: '#fdba74', border: '#c2410c' }} }},
          Term: {{ color: {{ background: '#93c5fd', border: '#1d4ed8' }} }},
          Encyclopedia: {{ color: {{ background: '#86efac', border: '#15803d' }} }}
        }},
        physics: {{
          stabilization: true,
          barnesHut: {{
            gravitationalConstant: -2500,
            springLength: 95,
            springConstant: 0.04
          }}
        }},
        interaction: {{ hover: true, navigationButtons: true }}
      }}
    );

    function showTip(html, evt) {{
      if (!html) {{
        tip.style.display = 'none';
        return;
      }}
      tip.innerHTML = html;
      tip.style.display = 'block';
      const pad = 14;
      let x = (evt && evt.clientX != null ? evt.clientX : 0) + pad;
      let y = (evt && evt.clientY != null ? evt.clientY : 0) + pad;
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
      const rect = tip.getBoundingClientRect();
      if (rect.right > window.innerWidth - 8) {{
        tip.style.left = Math.max(8, window.innerWidth - rect.width - 8) + 'px';
      }}
      if (rect.bottom > window.innerHeight - 8) {{
        tip.style.top = Math.max(8, window.innerHeight - rect.height - 8) + 'px';
      }}
    }}

    network.on('hoverNode', function (params) {{
      const node = nodes.get(params.node);
      const html = (node && (node.tooltip || node.label)) || '';
      showTip(html, params.event && params.event.srcEvent);
    }});
    network.on('blurNode', function () {{ tip.style.display = 'none'; }});
    network.on('dragStart', function () {{ tip.style.display = 'none'; }});
    container.addEventListener('mousemove', function (evt) {{
      if (tip.style.display === 'block') showTip(tip.innerHTML, evt);
    }});

    function setStatus(msg, isErr) {{
      statusEl.textContent = msg || '';
      statusEl.className = isErr ? 'err' : '';
    }}

    function applyGraph(data) {{
      nodes.clear();
      edges.clear();
      nodes.add(data.nodes || []);
      edges.add(data.edges || []);
      const c = data.counts || {{}};
      const n = c.nodes != null ? c.nodes : (data.nodes || []).length;
      const e = c.edges != null ? c.edges : (data.edges || []).length;
      const extra = [];
      if (c.clusters != null) extra.push(c.clusters + ' clusters');
      if (c.islands != null) extra.push(c.islands + ' islands');
      stats.textContent = n + ' nodes · ' + e + ' edges'
        + (extra.length ? ' · ' + extra.join(' · ') : '')
        + ' — drag, zoom, hover';
      const t = data.timing_ms || {{}};
      setStatus(
        'resolution=' + data.resolution
        + (t.total != null ? ' · rebuilt in ' + t.total + ' ms' : '')
      );
      network.fit({{ animation: false }});
    }}

    let debounceTimer = null;
    let inflight = 0;
    async function fetchResolution(res) {{
      if (!apiEnabled) {{
        setStatus('Slider needs pipeline kg --view (file:// has no API)', true);
        return;
      }}
      const my = ++inflight;
      setStatus('rebuilding at resolution=' + res + '…');
      try {{
        const resp = await fetch('/api/graph?resolution=' + encodeURIComponent(res));
        const data = await resp.json();
        if (my !== inflight) return;
        if (!resp.ok || !data.ok) {{
          setStatus((data && data.error) || ('HTTP ' + resp.status), true);
          return;
        }}
        applyGraph(data);
      }} catch (err) {{
        if (my !== inflight) return;
        setStatus(String(err), true);
      }}
    }}

    slider.addEventListener('input', function () {{
      resValue.textContent = slider.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {{
        fetchResolution(slider.value);
      }}, 150);
    }});

    if (apiEnabled) {{
      setStatus('Live API ready — drag the slider to re-cluster');
    }} else {{
      slider.disabled = true;
      setStatus('Open via pipeline kg --view for live rebuild', true);
    }}
  </script>
</body>
</html>
"""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def build_kg(
    workdir: Path,
    *,
    kg_links: Sequence[str] = DEFAULT_KG_LINKS,
    max_island: int = DEFAULT_MAX_ISLAND,
    min_paper_count: int = DEFAULT_KG_MIN_PAPER_COUNT,
    max_terms: int = DEFAULT_KG_MAX_TERMS,
    document_limit: Optional[int] = None,
    title: Optional[str] = None,
    write_html: bool = True,
    open_browser: bool = False,
) -> Dict[str, Any]:
    """Assemble KG artifacts under ``workdir/kg/``."""
    workdir = Path(workdir)
    links = tuple(
        p.strip().lower()
        for p in (kg_links or DEFAULT_KG_LINKS)
        if str(p).strip()
    )
    if not links:
        raise CorpusError("kg_links must include at least one source")

    all_nodes: Dict[str, Dict[str, Any]] = {}
    all_edges: Dict[str, Dict[str, Any]] = {}
    used: List[str] = []
    skipped: List[str] = []
    allowed: Optional[Set[str]] = None
    n_papers_map: Dict[str, int] = {}
    term_source = ""
    allowed_papers: Optional[Set[str]] = None
    if document_limit is not None:
        from semantic_corpus.cluster_review.encyclopedia import (
            _document_ids_capped,
        )

        allowed_papers = _document_ids_capped(workdir, document_limit)

    if "clusters" in links:
        allowed, n_papers_map, term_source = select_kg_terms(
            workdir,
            min_paper_count=int(min_paper_count),
            max_terms=int(max_terms),
        )
        nodes, edges = links_from_clusters(
            workdir,
            allowed_phrases=allowed,
            allowed_papers=allowed_papers,
            n_papers_map=n_papers_map,
        )
        for n in nodes:
            all_nodes[n["id"]] = n
        for e in edges:
            all_edges[e["id"]] = e
        used.append("clusters")
    else:
        skipped.append("clusters")

    synonym_stats: Dict[str, Any] = {
        "synonym_groups": 0,
        "terms_merged": 0,
        "encyclopedia_dropped": 0,
        "synonym_map": {},
    }
    if "wikipedia" in links or "wikidata" in links:
        # Attach encyclopedia edges, then collapse synonym bridges and drop
        # 1-connected green nodes (blue—green—blue → one blue).
        enc_nodes, enc_edges = links_from_encyclopedia(workdir)
        enc_by_id = {n["id"]: n for n in enc_nodes}
        if enc_nodes or enc_edges:
            for e in enc_edges:
                term_end = e["from"] if e["from"].startswith("term:") else e["to"]
                wiki_end = e["to"] if e["to"].startswith("wiki:") else e["from"]
                phrase = term_end.split(":", 1)[-1]
                if allowed is not None and phrase not in allowed:
                    continue
                if term_end not in all_nodes:
                    continue
                if wiki_end in enc_by_id:
                    all_nodes.setdefault(wiki_end, enc_by_id[wiki_end])
                all_edges[e["id"]] = e
            all_nodes, all_edges, synonym_stats = collapse_encyclopedia_synonyms(
                all_nodes, all_edges
            )
            if "wikipedia" in links:
                used.append("wikipedia")
            if "wikidata" in links:
                used.append("wikidata")
        else:
            if "wikipedia" in links:
                skipped.append("wikipedia (no encyclopedia/entries.json)")
            if "wikidata" in links:
                skipped.append("wikidata (no encyclopedia/entries.json)")

    nodes_list = list(all_nodes.values())
    edges_list = list(all_edges.values())
    # Drop edges to missing nodes
    node_ids = {n["id"] for n in nodes_list}
    edges_list = [
        e
        for e in edges_list
        if (e.get("from") or e.get("source")) in node_ids
        and (e.get("to") or e.get("target")) in node_ids
    ]

    islands = detect_islands(nodes_list, edges_list, max_island=max_island)
    enc_title = title or f"Knowledge graph ({workdir.name})"

    out = kg_dir(workdir)
    out.mkdir(parents=True, exist_ok=True)
    graph_doc = {
        "step": "kg",
        "workdir": str(workdir.resolve()),
        "params": {
            "kg_links": list(links),
            "kg_links_used": used,
            "kg_links_skipped": skipped,
            "max_island": int(max_island),
            "min_paper_count": int(min_paper_count),
            "max_terms": int(max_terms),
            "document_limit": (
                int(document_limit) if document_limit is not None else None
            ),
            "term_filter_source": term_source,
            "terms_selected": len(allowed) if allowed is not None else None,
            "synonym_groups": synonym_stats.get("synonym_groups"),
            "terms_merged": synonym_stats.get("terms_merged"),
            "encyclopedia_dropped": synonym_stats.get("encyclopedia_dropped"),
        },
        "synonym_map": synonym_stats.get("synonym_map") or {},
        "nodes": nodes_list,
        "edges": edges_list,
        "counts": {
            "nodes": len(nodes_list),
            "edges": len(edges_list),
            "papers": sum(1 for n in nodes_list if n.get("kind") == "paper"),
            "terms": sum(1 for n in nodes_list if n.get("kind") == "term"),
            "encyclopedia": sum(
                1 for n in nodes_list if n.get("kind") == "encyclopedia"
            ),
            "islands": len(islands),
            "synonym_groups": synonym_stats.get("synonym_groups"),
            "terms_merged": synonym_stats.get("terms_merged"),
        },
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    gpath = graph_path(workdir)
    gpath.write_text(json.dumps(graph_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ipath = islands_path(workdir)
    ipath.write_text(
        json.dumps(
            {
                "max_island": int(max_island),
                "island_count": len(islands),
                "islands": islands,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = {
        "step": "kg",
        "workdir": str(workdir.resolve()),
        "graph_path": str(gpath.resolve()),
        "islands_path": str(ipath.resolve()),
        "params": graph_doc["params"],
        "counts": graph_doc["counts"],
        "written_at": graph_doc["written_at"],
    }

    html_out = None
    if write_html:
        resolution = 1.0
        csum = _load_json(workdir / "clusters" / "graph_summary.json") or {}
        try:
            resolution = float((csum.get("params") or {}).get("resolution") or 1.0)
        except (TypeError, ValueError):
            resolution = 1.0
        html_out = write_kg_html(
            nodes_list,
            edges_list,
            html_path(workdir),
            title=enc_title,
            resolution=resolution,
        )
        summary["html_path"] = str(html_out.resolve())
        if open_browser:
            webbrowser.open(html_out.resolve().as_uri())

    spath = summary_path(workdir)
    spath.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary["summary_path"] = str(spath.resolve())
    return summary


def kg_is_current(
    workdir: Path,
    *,
    kg_links: Sequence[str],
    max_island: int,
    min_paper_count: int = DEFAULT_KG_MIN_PAPER_COUNT,
    max_terms: int = DEFAULT_KG_MAX_TERMS,
) -> bool:
    summary = _load_json(summary_path(workdir))
    graph = _load_json(graph_path(workdir))
    if not summary or not graph:
        return False
    if not html_path(workdir).is_file():
        return False
    params = summary.get("params") or {}
    want = [p.strip().lower() for p in kg_links if str(p).strip()]
    have = list(params.get("kg_links") or [])
    if have != want:
        return False
    if int(params.get("max_island") or 0) != int(max_island):
        return False
    if int(params.get("min_paper_count") or 0) != int(min_paper_count):
        return False
    if int(params.get("max_terms") or 0) != int(max_terms):
        return False
    clusters = Path(workdir) / "clusters" / "clusters.json"
    if clusters.is_file() and clusters.stat().st_mtime > summary_path(workdir).stat().st_mtime:
        return False
    return True
