"""Validate document bytes before writing XML/PDF to disk.

Never save Europe PMC (or other) HTTP error JSON/HTML as ``.xml`` / ``.pdf``,
and never overwrite a valid existing file with an error payload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union


PathLike = Union[str, Path]
MIN_PDF_BYTES = 64
MIN_XML_BYTES = 16


def looks_like_pdf(content: bytes) -> bool:
    """True if body starts with PDF magic (rejects HTML/JSON error pages)."""
    if not content or len(content) < MIN_PDF_BYTES:
        return False
    return content.startswith(b"%PDF")


def looks_like_fulltext_xml(content: bytes) -> bool:
    """True if body looks like XML/JATS, not a JSON/HTML error stub."""
    if not content or len(content) < MIN_XML_BYTES:
        return False
    head = content.lstrip()
    if head.startswith(b"\xef\xbb\xbf"):
        head = head[3:].lstrip()
    if not head or head.startswith((b"{", b"[")):
        return False
    lower = head[:64].lower()
    if lower.startswith((b"<!doctype", b"<!--", b"<html")):
        return False
    return head.startswith(b"<")


def http_status_from_error_body(content: bytes) -> Optional[int]:
    """Read ``status`` from a Spring Boot JSON error body, if present."""
    try:
        data = json.loads(content.decode("utf-8", errors="replace"))
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or "status" not in data:
        return None
    try:
        code = int(data["status"])
    except (TypeError, ValueError):
        return None
    return code if 100 <= code <= 599 else None


def is_valid_document_bytes(fmt: str, content: bytes) -> bool:
    """True if ``content`` is acceptable to save as ``fmt`` (xml/pdf/…)."""
    kind = (fmt or "").strip().lower()
    if kind == "pdf":
        return looks_like_pdf(content)
    if kind == "xml":
        return looks_like_fulltext_xml(content)
    # Unknown formats: reject obvious JSON/HTML error pages only.
    if not content:
        return False
    head = content.lstrip()[:64]
    if head.startswith((b"{", b"[")):
        return False
    lower = head.lower()
    if lower.startswith((b"<!doctype", b"<html")):
        return False
    return True


def is_valid_document_file(path: PathLike, fmt: str) -> bool:
    """True if ``path`` exists and its contents look like a real ``fmt`` document."""
    path = Path(path)
    if not path.is_file():
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    kind = (fmt or "").strip().lower()
    if kind == "pdf" and size < MIN_PDF_BYTES:
        return False
    if kind == "xml" and size < MIN_XML_BYTES:
        return False
    if size <= 0:
        return False
    try:
        with open(path, "rb") as handle:
            # Enough for magic / stub detection; XML may be huge.
            head = handle.read(max(4096, MIN_PDF_BYTES))
    except OSError:
        return False
    return is_valid_document_bytes(kind, head if kind == "pdf" else head)


def safe_write_document(
    path: PathLike,
    content: bytes,
    *,
    fmt: str,
) -> bool:
    """Write ``content`` only if valid; never replace a valid file with bad bytes.

    - Rejects error JSON/HTML stubs (returns False, writes nothing).
    - If ``path`` already holds a valid document, leaves it unchanged.
    - If ``path`` holds an invalid stub, removes it and writes valid content.
    - Uses a ``.partial`` sibling then rename so a crash cannot leave a half
      error file under the final name.

    Returns:
        True if ``path`` is a valid document afterward.
    """
    path = Path(path)
    kind = (fmt or "").strip().lower()

    if path.is_file() and is_valid_document_file(path, kind):
        # Keep good files; never overwrite them (including with errors).
        return True

    if not is_valid_document_bytes(kind, content):
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        # Invalid stub (or empty) — remove so we can replace with real content.
        try:
            path.unlink()
        except OSError:
            return False

    partial = path.with_name(path.name + ".partial")
    try:
        partial.write_bytes(content)
        if not is_valid_document_file(partial, kind):
            partial.unlink(missing_ok=True)
            return False
        partial.replace(path)
    except OSError:
        partial.unlink(missing_ok=True)
        return False

    return is_valid_document_file(path, kind)
