"""Live scrolling title feed while collecting / downloading papers."""

from __future__ import annotations

import re
import shutil
import sys
from collections import deque
from typing import Deque, List, Optional, TextIO


_TAG_RE = re.compile(r"<[^>]+>")


def clean_title(text: Optional[str], *, max_len: int = 96) -> str:
    """Strip light markup and compress whitespace for one-line display."""
    raw = _TAG_RE.sub(" ", str(text or "")).replace("\n", " ").strip()
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return "(no title)"
    if len(raw) > max_len:
        return raw[: max_len - 1] + "…"
    return raw


def _term_width(stream: TextIO, default: int = 88) -> int:
    try:
        return max(40, shutil.get_terminal_size(fallback=(default, 24)).columns)
    except OSError:
        return default


def _clip(text: str, width: int) -> str:
    if width < 8:
        return text[:width]
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


class CollectTitleScroller:
    """Fixed-height scrolling window of recent paper titles (ANSI terminal).

    Only successful keeps (``ok`` / ``skip``) count toward ``limit``.
    Failed attempts update the status line but do not inflate the counter.
    Falls back to one printed line per keep when stderr is not a TTY.
    """

    def __init__(
        self,
        *,
        limit: int,
        height: int = 12,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.limit = max(1, int(limit))
        self.height = max(3, int(height))
        self.stream = stream or sys.stderr
        self.lines: Deque[str] = deque(maxlen=self.height)
        self.kept = 0
        self.n_ok = 0
        self.n_skip = 0
        self.n_fail = 0
        self._live = bool(getattr(self.stream, "isatty", lambda: False)())
        self._drawn = 0  # terminal rows currently occupied by the panel
        self._started = False
        self._width = _term_width(self.stream)

    def start(self, *, query: str, repository: str) -> None:
        self._started = True
        self._width = _term_width(self.stream)
        q = clean_title(query, max_len=60)
        msg = f"[collect] {repository} · query={q!r} · limit={self.limit}"
        print(msg, file=self.stream, flush=True)
        if self._live:
            self._drawn = 0
            self._redraw(status="searching / downloading…")

    def add(
        self,
        *,
        title: str,
        paper_id: str = "",
        status: str = "ok",
    ) -> None:
        if not self._started:
            self.start(query="", repository="")

        if status == "fail":
            self.n_fail += 1
            if self._live:
                self._redraw(status=self._status_line())
            # Do not count fails toward limit or scroll list.
            return

        if status == "skip":
            self.n_skip += 1
        else:
            self.n_ok += 1
            status = "ok"
        self.kept += 1

        label = clean_title(title, max_len=max(24, self._width - 28))
        short_id = (paper_id or "").replace("europe_pmc_", "")
        prefix = "+" if status == "ok" else "="
        line = f"{prefix} [{self.kept:>3}/{self.limit}] {label}"
        if short_id:
            line = f"{line}  ({short_id})"
        self.lines.append(_clip(line, self._width - 2))

        if self._live:
            self._redraw(status=self._status_line())
        else:
            print(line, file=self.stream, flush=True)

    def finish(self, *, downloaded: int = 0, skipped: int = 0) -> None:
        # Prefer internal tallies; fall back to caller args if unused.
        if self.kept:
            status = (
                f"done · kept={self.kept}/{self.limit} "
                f"(new={self.n_ok}, cached={self.n_skip}, failed={self.n_fail})"
            )
        else:
            status = f"done · downloaded={downloaded}"
            if skipped:
                status += f" · already present={skipped}"
        if self._live:
            self._redraw(status=status)
            print(file=self.stream, flush=True)
            self._drawn = 0
        else:
            print(f"[collect] {status}", file=self.stream, flush=True)

    def _status_line(self) -> str:
        bits = [f"kept {self.kept}/{self.limit}"]
        if self.n_fail:
            bits.append(f"failed={self.n_fail}")
        return " · ".join(bits)

    def _redraw(self, *, status: str) -> None:
        out = self.stream
        width = self._width
        inner = max(8, width - 2)
        if self._drawn:
            out.write(f"\x1b[{self._drawn}A")
        out.write("\x1b[0J")

        border = "─" * inner
        rows: List[str] = [
            _clip(f"┌─ collect  {status}", width),
            _clip(f"├{border}", width),
        ]
        visible = list(self.lines)
        for _ in range(max(0, self.height - len(visible))):
            rows.append("│")
        for line in visible:
            rows.append(_clip(f"│ {line}", width))
        rows.append(_clip(f"└{border}", width))

        # Pad each row to avoid leftover characters if width shrank.
        out.write("\n".join(rows) + "\n")
        out.flush()
        self._drawn = len(rows)


def title_from_paper(paper: dict) -> str:
    return clean_title(paper.get("title") or paper.get("paper_title") or "")
