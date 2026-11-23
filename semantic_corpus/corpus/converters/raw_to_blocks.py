"""Stage B for raw text: split into paragraph text_blocks with heuristic ids."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union
import html as html_lib


def raw_text_to_semantic(
    text: str,
    *,
    paper_id: str = "doc",
    id_scheme: str = "v1",
) -> Dict[str, Any]:
    """Split blank-line-separated chunks into paragraph text_blocks + HTML.

    Args:
        text: Raw Unicode text without coordinates.
        paper_id: Document id prefix.
        id_scheme: Stamp field.

    Returns:
        Dict with ``paper_id``, ``html``, ``blocks``, ``id_scheme``.
    """
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    blocks: List[Dict[str, Any]] = []
    parts: List[str] = ['<!DOCTYPE html><html><body>']
    for i, chunk in enumerate(chunks, start=1):
        block_id = f"{paper_id}#p-{i:03d}"
        blocks.append(
            {
                "id": block_id,
                "kind": "paragraph",
                "text": " ".join(chunk.split()),
                "order": i,
            }
        )
        escaped = html_lib.escape(chunk).replace("\n", "<br/>\n")
        parts.append(f'<p id="{html_lib.escape(block_id)}" data-tb-kind="paragraph">{escaped}</p>')
    parts.append("</body></html>")
    return {
        "paper_id": paper_id,
        "html": "\n".join(parts),
        "blocks": blocks,
        "id_scheme": id_scheme,
    }


def raw_file_to_semantic(
    path: Union[Path, str],
    *,
    paper_id: str = "doc",
    id_scheme: str = "v1",
) -> Dict[str, Any]:
    """Load a UTF-8 text file and convert to semantic_text-shaped dict."""
    text = Path(path).read_text(encoding="utf-8")
    return raw_text_to_semantic(text, paper_id=paper_id, id_scheme=id_scheme)
