#!/usr/bin/env python3
"""Build output_from_pdf.html via the legacy extractor → sectioner pipeline.

Uses ``semantic_corpus.corpus.legacy`` so the middle compare pane is indexed HTML
(with text_block ids), not a raw line dump.

  python examples/pdf_html_compare/build_compare.py
  python examples/pdf_html_compare/build_compare.py --engine docling
  python examples/pdf_html_compare/build_compare.py --engine amilib --refine amilib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAIR = ROOT / "tests" / "resources" / "input_adapters" / "oa_pdf_html_pair"
PDF = PAIR / "ClimateEU_PMC7719169.pdf"
OUT_DIR = Path(__file__).resolve().parent
OUT_HTML = OUT_DIR / "output_from_pdf.html"
OUT_JSON = OUT_DIR / "output_from_pdf.indexed.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engine",
        choices=("auto", "pymupdf", "docling", "amilib"),
        default="pymupdf",
        help="Extractor backend (default pymupdf = fast baseline with soft line-join)",
    )
    parser.add_argument(
        "--refine",
        choices=("auto", "none", "amilib"),
        default="auto",
        help="Sectioner refine (amilib PageJoiner when positioned HTML + scripts available)",
    )
    parser.add_argument(
        "--no-ids",
        action="store_true",
        help="Write extract HTML only (skip sectioner id minting) — not recommended",
    )
    args = parser.parse_args()
    if not PDF.is_file():
        print(f"Missing PDF fixture: {PDF}", file=sys.stderr)
        return 1

    from semantic_corpus.corpus.legacy import legacy_to_indexed_text, list_extractors
    from semantic_corpus.corpus.legacy.extractors import get_extractor

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUT_DIR / "_extract_work"
    work.mkdir(parents=True, exist_ok=True)

    if args.no_ids:
        extract = get_extractor(args.engine).extract(PDF, outdir=work)
        OUT_HTML.write_text(extract.html, encoding="utf-8")
        print(f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes) via {extract.engine} (no ids)")
    else:
        indexed = legacy_to_indexed_text(
            PDF,
            extractor=args.engine,
            paper_id="ClimateEU_PMC7719169",
            refine=args.refine,
            outdir=work,
            write_html=True,
        )
        # Wrap with a light compare chrome so the pane is readable alone
        body = indexed["html"]
        if "<body" not in body.lower():
            body = f"<body>{body}</body>"
        chrome = (
            "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
            "<title>ClimateEU — indexed HTML from PDF</title>"
            "<style>body{font-family:Georgia,serif;max-width:48rem;margin:1.5rem auto;"
            "padding:0 1rem;line-height:1.45;} "
            "header{border-bottom:1px solid #ccc;margin-bottom:1rem;padding-bottom:.75rem;} "
            "[data-tb-kind]{margin:.4rem 0;} "
            ".meta{font-size:.85rem;color:#555;}</style></head>"
            f"<header><h1>Output HTML from PDF</h1>"
            f"<p class='meta'>extractor={indexed['extractor']} · "
            f"blocks={len(indexed['blocks'])} · refine={args.refine}</p>"
            f"<p class='meta'>available: {', '.join(list_extractors())}</p></header>"
        )
        # Prefer writing the sectioned document as-is when it already has html/body
        if body.lstrip().lower().startswith("<!doctype") or body.lstrip().lower().startswith(
            "<html"
        ):
            OUT_HTML.write_text(body, encoding="utf-8")
        else:
            OUT_HTML.write_text(chrome + body + "</html>", encoding="utf-8")
        import json

        OUT_JSON.write_text(
            json.dumps(
                {
                    "paper_id": indexed["paper_id"],
                    "extractor": indexed["extractor"],
                    "block_count": len(indexed["blocks"]),
                    "warnings": indexed.get("warnings", []),
                    "blocks": indexed["blocks"][:50],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(
            f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes) via {indexed['extractor']}; "
            f"{len(indexed['blocks'])} text_blocks"
        )
        for w in indexed.get("warnings") or []:
            print(f"  warn: {w}")

    print(f"Open in a browser: {OUT_DIR / 'compare.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
