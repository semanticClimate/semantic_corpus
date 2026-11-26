#!/usr/bin/env python3
"""Sample: IPCC figure-caption ``indexed_text`` + term list → bipartite KG.

``indexed_text`` types/loaders come from ``semantic_corpus.corpus.types``
(shared with chatbot and other consumers). This script only owns bipartite /
display concerns.

  python examples/phrases_kg_ipcc_captions/build_bipartite_kg.py
  python examples/phrases_kg_ipcc_captions/build_bipartite_kg.py --out /tmp/ipcc_kg
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_corpus.corpus.types import (  # noqa: E402
    INDEXED_JSON_GLOB,
    BlockFields,
    BlockKind,
    IndexedDocType,
    IndexedTextFields,
    MetadataFields,
    blocks_of_kinds,
    load_indexed_texts,
)

# ---------------------------------------------------------------------------
# Sample paths / filenames (example-local)
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).resolve().parent
DATA_DIR = SAMPLE_DIR / "data"
DEFAULT_OUT_DIR = SAMPLE_DIR / "out"

TERMS_FILENAME = "terms.json"
OUT_GRAPHML_NAME = "ipcc_captions_bipartite.graphml"
OUT_EDGES_JSON_NAME = "ipcc_captions_bipartite.edges.json"
OUT_PNG_NAME = "ipcc_captions_bipartite.png"

# ---------------------------------------------------------------------------
# Bipartite / KG-local vocabulary (not part of indexed_text)
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    TERM = "term"
    CAPTION = "caption"


class EdgeType(str, Enum):
    OCCURS_IN = "occurs_in"


class BipartiteSide(IntEnum):
    TERM = 0
    CAPTION = 1


class GraphFields:
    """Attribute keys written onto NetworkX nodes/edges / edges JSON."""

    NODE_TYPE = "node_type"
    LABEL = "label"
    BIPARTITE = "bipartite"
    EDGE_TYPE = "edge_type"
    TERM = "term"
    CAPTION_ID = "caption_id"


DISPLAY_EDGE_HEADER = "\n=== Bipartite edges (term → figcaption) ===\n"
DISPLAY_TEXT_MAX = 90
NODE_TEXT_PREVIEW_MAX = 160
LABEL_DRAW_MAX = 28
PNG_TITLE = "IPCC figcaption ↔ term (bipartite)"
PNG_DPI = 150
PNG_FIGSIZE = (12, 8)
COLOR_TERM = "#4C78A8"
COLOR_CAPTION = "#F58518"
TERM_NODE_SIZE = 600
CAPTION_NODE_SIZE = 900

DEFAULT_BLOCK_KINDS: Tuple[str, ...] = (BlockKind.FIGCAPTION.value,)

_TERM_BOUNDARY_TMPL = r"(?<!\w){term}(?!\w)"


def _term_pattern(term: str) -> re.Pattern:
    return re.compile(
        _TERM_BOUNDARY_TMPL.format(term=re.escape(term)),
        re.IGNORECASE,
    )


def load_terms(path: Path) -> List[str]:
    """Load a JSON array of term strings (phrases_kg Goal-1 skip shape)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not all(isinstance(t, str) for t in raw):
        raise ValueError(f"{path}: expected a JSON array of strings")
    return sorted({t.strip() for t in raw if t.strip()}, key=len, reverse=True)


def figcaption_blocks(docs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return blocks_of_kinds(docs, (BlockKind.FIGCAPTION,))


def term_matches(term: str, text: str) -> bool:
    return _term_pattern(term).search(text) is not None


def build_bipartite_edges(
    captions: Sequence[Dict[str, Any]], terms: Sequence[str]
) -> List[Tuple[str, str, str]]:
    edges: List[Tuple[str, str, str]] = []
    for cap in captions:
        text = cap[BlockFields.TEXT]
        hit_spans: List[Tuple[int, int]] = []
        for term in terms:
            for m in _term_pattern(term).finditer(text):
                span = (m.start(), m.end())
                if any(s <= span[0] and span[1] <= e for s, e in hit_spans):
                    continue
                hit_spans.append(span)
                edges.append((term, cap[BlockFields.ID], term))
                break
    return edges


def build_networkx_graph(
    captions: Sequence[Dict[str, Any]],
    terms: Sequence[str],
    edges: Sequence[Tuple[str, str, str]],
):
    try:
        import networkx as nx
    except ImportError as exc:
        raise SystemExit(
            "networkx is required: pip install networkx  (or semantic_corpus[cluster_review])"
        ) from exc

    G = nx.Graph()
    term_set = {t for t, _, _ in edges}
    cap_ids = {c for _, c, _ in edges}
    for t in sorted(term_set):
        G.add_node(
            t,
            **{
                GraphFields.BIPARTITE: int(BipartiteSide.TERM),
                GraphFields.NODE_TYPE: NodeType.TERM.value,
                GraphFields.LABEL: t,
            },
        )
    for cap in captions:
        if cap[BlockFields.ID] not in cap_ids:
            continue
        G.add_node(
            cap[BlockFields.ID],
            **{
                GraphFields.BIPARTITE: int(BipartiteSide.CAPTION),
                GraphFields.NODE_TYPE: NodeType.CAPTION.value,
                GraphFields.LABEL: cap[BlockFields.ID].split("#")[-1],
                IndexedTextFields.PAPER_ID: cap[IndexedTextFields.PAPER_ID],
                MetadataFields.CITATION_LABEL: cap[MetadataFields.CITATION_LABEL],
                BlockFields.TEXT: cap[BlockFields.TEXT][:NODE_TEXT_PREVIEW_MAX],
            },
        )
    for term, cap_id, _ in edges:
        G.add_edge(
            term, cap_id, **{GraphFields.EDGE_TYPE: EdgeType.OCCURS_IN.value}
        )
    return G


def print_adjacency(
    edges: Sequence[Tuple[str, str, str]], captions: Sequence[Dict[str, Any]]
) -> None:
    by_cap = {c[BlockFields.ID]: c for c in captions}
    print(DISPLAY_EDGE_HEADER)
    for term, cap_id, _ in sorted(edges, key=lambda e: (e[1], e[0].lower())):
        short = by_cap[cap_id][BlockFields.TEXT]
        if len(short) > DISPLAY_TEXT_MAX:
            short = short[: DISPLAY_TEXT_MAX - 3] + "..."
        print(f"  [{term}]  —  {cap_id}")
        print(f"           {short}")
    print(
        f"\n{len(edges)} edges · {len({e[0] for e in edges})} terms · "
        f"{len({e[1] for e in edges})} captions with ≥1 term\n"
    )


def write_outputs(
    G, out_dir: Path, edges: Sequence[Tuple[str, str, str]]
) -> None:
    import networkx as nx

    out_dir.mkdir(parents=True, exist_ok=True)
    graphml = out_dir / OUT_GRAPHML_NAME
    nx.write_graphml(G, graphml)
    edges_json = out_dir / OUT_EDGES_JSON_NAME
    edges_json.write_text(
        json.dumps(
            [
                {
                    GraphFields.TERM: t,
                    GraphFields.CAPTION_ID: c,
                    GraphFields.EDGE_TYPE: EdgeType.OCCURS_IN.value,
                }
                for t, c, _ in edges
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {graphml}")
    print(f"Wrote {edges_json}")

    try:
        import matplotlib.pyplot as plt
        from networkx.drawing.layout import bipartite_layout
    except ImportError:
        print("(skip PNG: install matplotlib for a drawing)")
        return

    term_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get(GraphFields.BIPARTITE) == int(BipartiteSide.TERM)
    ]
    cap_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get(GraphFields.BIPARTITE) == int(BipartiteSide.CAPTION)
    ]
    pos = bipartite_layout(G, term_nodes, align="vertical", scale=2.0)
    plt.figure(figsize=PNG_FIGSIZE)
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=term_nodes,
        node_color=COLOR_TERM,
        node_size=TERM_NODE_SIZE,
        label=NodeType.TERM.value,
    )
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=cap_nodes,
        node_color=COLOR_CAPTION,
        node_size=CAPTION_NODE_SIZE,
        label=NodeType.CAPTION.value,
    )
    nx.draw_networkx_edges(G, pos, alpha=0.4)
    labels = {
        n: (d.get(GraphFields.LABEL) or n)[:LABEL_DRAW_MAX]
        for n, d in G.nodes(data=True)
    }
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7)
    plt.title(PNG_TITLE)
    plt.axis("off")
    plt.tight_layout()
    png = out_dir / OUT_PNG_NAME
    plt.savefig(png, dpi=PNG_DPI)
    plt.close()
    print(f"Wrote {png}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_DIR,
        help=f"Directory with {INDEXED_JSON_GLOB} and {TERMS_FILENAME}",
    )
    parser.add_argument(
        "--terms",
        type=Path,
        default=None,
        help=f"Override path to {TERMS_FILENAME}",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write GraphML / edges JSON / optional PNG here",
    )
    parser.add_argument(
        "--kinds",
        nargs="+",
        default=list(DEFAULT_BLOCK_KINDS),
        choices=[k.value for k in BlockKind],
        help="text_block kinds to use as document-side nodes",
    )
    args = parser.parse_args()
    data_dir: Path = args.data
    terms_path = args.terms or (data_dir / TERMS_FILENAME)
    indexed_paths = sorted(data_dir.glob(INDEXED_JSON_GLOB))
    if not indexed_paths:
        print(f"No {INDEXED_JSON_GLOB} under {data_dir}", file=sys.stderr)
        return 1
    if not terms_path.is_file():
        print(f"Missing terms file: {terms_path}", file=sys.stderr)
        return 1

    docs = load_indexed_texts(indexed_paths)
    terms = load_terms(terms_path)
    captions = blocks_of_kinds(docs, args.kinds)

    print(
        f"Loaded {len(docs)} {IndexedDocType.INDEXED_TEXT.value} docs, "
        f"{len(captions)} blocks (kinds={args.kinds}), {len(terms)} terms"
    )
    edges = build_bipartite_edges(captions, terms)
    if not edges:
        print(
            f"No term–caption matches; check {TERMS_FILENAME} spelling.",
            file=sys.stderr,
        )
        return 2

    print_adjacency(edges, captions)
    G = build_networkx_graph(captions, terms, edges)
    write_outputs(G, args.out or DEFAULT_OUT_DIR, edges)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
