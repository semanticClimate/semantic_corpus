"""Novice-friendly Europe PMC preflight — per-stream (JSON / XML / PDF)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Optional, TextIO, Tuple

import requests

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.repositories.document_content import (
    http_status_from_error_body,
    looks_like_fulltext_xml,
    looks_like_pdf,
)
from semantic_corpus.repositories.epmc_streams import (
    STREAM_JSON,
    STREAM_PDF,
    STREAM_XML,
    EpmcStreamBoard,
    print_stream_board,
)
from semantic_corpus.repositories.europe_pmc import (
    EuropePMCRepository,
    SEARCH_TIMEOUT_SECONDS,
)

# Stable open-access article used only to probe full-text health.
_PROBE_PMCID = "PMC3112747"
_PROBE_QUERY = "SRC:MED AND OPEN_ACCESS:Y"
_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
_TIMEOUT = min(20, SEARCH_TIMEOUT_SECONDS)


@dataclass(frozen=True)
class StatusGuide:
    """Plain-language explanation of an HTTP / probe outcome."""

    code_label: str
    meaning: str
    advice: str
    severity: str  # ok | warn | fail


@dataclass
class ProbeResult:
    name: str  # json | xml | pdf
    ok: bool
    status_code: Optional[int]
    guide: StatusGuide
    detail: str = ""


@dataclass
class EpmcDiagnostic:
    probes: List[ProbeResult]
    board: EpmcStreamBoard

    @property
    def ok(self) -> bool:
        """True when at least the JSON/search stream works (job can start)."""
        return self.board.is_active(STREAM_JSON)

    @property
    def all_streams_ok(self) -> bool:
        return all(self.board.is_active(n) for n in (STREAM_JSON, STREAM_XML, STREAM_PDF))

    @property
    def blocking(self) -> List[ProbeResult]:
        return [p for p in self.probes if not p.ok and p.name == STREAM_JSON]


class EpmcUnavailable(CorpusError):
    """Europe PMC JSON/search stream failed; cannot collect."""


def explain_status(status_code: Optional[int], *, kind: str = "http") -> StatusGuide:
    """Explain a status code in language suitable for novices."""
    if status_code is None:
        if kind == "timeout":
            return StatusGuide(
                code_label="timeout",
                meaning="no answer in time",
                advice="Check your network, then try again in a few minutes.",
                severity="fail",
            )
        if kind == "connection":
            return StatusGuide(
                code_label="connection",
                meaning="could not reach Europe PMC",
                advice="Check internet / proxy settings, then retry.",
                severity="fail",
            )
        return StatusGuide(
            code_label="error",
            meaning="unexpected failure talking to Europe PMC",
            advice="Retry later. If it keeps happening, check network settings.",
            severity="fail",
        )

    code = int(status_code)
    if 200 <= code < 300:
        return StatusGuide(
            code_label="OK",
            meaning="Europe PMC answered normally",
            advice="Safe to use this stream.",
            severity="ok",
        )
    if code == 403:
        return StatusGuide(
            code_label="403",
            meaning="forbidden — often firewall, proxy, or bot block",
            advice="Try another network or wait; this is usually not your query.",
            severity="fail",
        )
    if code == 404:
        return StatusGuide(
            code_label="404",
            meaning="not found on Europe PMC",
            advice="This stream may be incomplete for some papers.",
            severity="warn",
        )
    if code == 429:
        return StatusGuide(
            code_label="429",
            meaning="rate limited — too many requests",
            advice="Wait several minutes, then retry with a smaller limit.",
            severity="fail",
        )
    if code == 500:
        return StatusGuide(
            code_label="500",
            meaning="server error on Europe PMC (not your query)",
            advice="This stream is discontinued for now; other streams continue.",
            severity="fail",
        )
    if code >= 500:
        return StatusGuide(
            code_label=str(code),
            meaning="server error on Europe PMC",
            advice="This stream is discontinued for now; other streams continue.",
            severity="fail",
        )
    if code >= 400:
        return StatusGuide(
            code_label=str(code),
            meaning="HTTP error talking to Europe PMC",
            advice="This stream is discontinued for now; other streams continue.",
            severity="fail",
        )
    return StatusGuide(
        code_label=str(code),
        meaning=f"unexpected HTTP status {code}",
        advice="Retry later.",
        severity="warn",
    )


def _probe_json_search() -> ProbeResult:
    url = f"{_BASE}/search"
    params = {
        "query": _PROBE_QUERY,
        "pageSize": 1,
        "format": "json",
        "resultType": "lite",
    }
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT)
    except requests.Timeout:
        return ProbeResult(STREAM_JSON, False, None, explain_status(None, kind="timeout"))
    except requests.RequestException:
        return ProbeResult(
            STREAM_JSON, False, None, explain_status(None, kind="connection")
        )

    code = response.status_code
    guide = explain_status(code)
    ok = guide.severity == "ok"
    if ok:
        try:
            response.json()
        except ValueError:
            ok = False
            guide = StatusGuide(
                code_label=str(code),
                meaning="search returned invalid JSON",
                advice="Come back later and retry.",
                severity="fail",
            )
    return ProbeResult(STREAM_JSON, ok, code, guide)


def _probe_xml(pmcid: str = _PROBE_PMCID) -> ProbeResult:
    url = f"{_BASE}/{pmcid}/fullTextXML"
    try:
        response = requests.get(url, timeout=_TIMEOUT)
    except requests.Timeout:
        return ProbeResult(STREAM_XML, False, None, explain_status(None, kind="timeout"))
    except requests.RequestException:
        return ProbeResult(
            STREAM_XML, False, None, explain_status(None, kind="connection")
        )

    code = response.status_code
    content = response.content or b""
    if code >= 400:
        return ProbeResult(STREAM_XML, False, code, explain_status(code))
    if not looks_like_fulltext_xml(content):
        stub = http_status_from_error_body(content)
        effective = stub or 500
        return ProbeResult(STREAM_XML, False, effective, explain_status(effective))
    return ProbeResult(STREAM_XML, True, code, explain_status(code))


def _probe_pdf(pmcid: str = _PROBE_PMCID) -> ProbeResult:
    repo = EuropePMCRepository()
    try:
        pdf = repo._download_pdf(pmcid, None, pmcid)
    except Exception:
        return ProbeResult(
            STREAM_PDF,
            False,
            500,
            explain_status(500),
            detail="pdf fetch failed",
        )
    if pdf and looks_like_pdf(pdf):
        return ProbeResult(STREAM_PDF, True, 200, explain_status(200))
    return ProbeResult(
        STREAM_PDF,
        False,
        500,
        explain_status(500),
        detail="no valid PDF from EPMC mirrors",
    )


def run_epmc_diagnostic() -> EpmcDiagnostic:
    """Probe JSON / XML / PDF streams independently."""
    probes = [_probe_json_search(), _probe_xml(), _probe_pdf()]
    board = EpmcStreamBoard()
    for probe in probes:
        if not probe.ok:
            board.disable(
                probe.name,
                reason=probe.guide.meaning,
                status_code=probe.status_code,
            )
    return EpmcDiagnostic(probes=probes, board=board)


def format_epmc_diagnostic(diag: EpmcDiagnostic) -> str:
    """Compact multi-line report for terminals."""
    labels = {
        STREAM_JSON: "JSON search",
        STREAM_XML: "XML full text",
        STREAM_PDF: "PDF",
    }
    lines: List[str] = ["┌─ Europe PMC streams"]
    for probe in diag.probes:
        label = labels.get(probe.name, probe.name)
        if probe.ok:
            lines.append(f"│ {label:<14} active")
        else:
            g = probe.guide
            lines.append(f"│ {label:<14} off {g.code_label} — {g.meaning}")
            lines.append(f"│                → {g.advice}")

    lines.append("│")
    if not diag.board.is_active(STREAM_JSON):
        lines.append("│ Stopped — JSON/search is required to collect.")
    elif diag.all_streams_ok:
        lines.append("│ Ready — all streams active.")
    else:
        lines.append("│ Continuing with active streams only.")
        if not diag.board.is_active(STREAM_XML) and diag.board.is_active(STREAM_PDF):
            lines.append("│ XML off → PDF (+ Docling → XML) when possible.")
    lines.append("└─")
    return "\n".join(lines)


def print_epmc_diagnostic(
    diag: Optional[EpmcDiagnostic] = None,
    *,
    stream: Optional[TextIO] = None,
) -> EpmcDiagnostic:
    """Run (unless provided) and print the diagnostic report."""
    out = stream or sys.stderr
    if diag is None:
        diag = run_epmc_diagnostic()
    print(format_epmc_diagnostic(diag), file=out, flush=True)
    return diag


def epmc_preflight(
    *,
    stream: Optional[TextIO] = None,
    abort: bool = True,
) -> Tuple[EpmcDiagnostic, EpmcStreamBoard]:
    """Run stream diagnostic before a job.

    Aborts only when the **JSON/search** stream is down. XML/PDF 500s disable
    those streams and the job continues.
    """
    diag = print_epmc_diagnostic(stream=stream)
    if abort and not diag.board.is_active(STREAM_JSON):
        raise EpmcUnavailable(
            "Europe PMC JSON/search unavailable. Come back later and retry."
        )
    return diag, diag.board


def short_status_blurb(status_code: int) -> str:
    """One-line blurb for status lines (e.g. fail breakdown help)."""
    guide = explain_status(status_code)
    return f"{guide.code_label} — {guide.meaning}. {guide.advice}"
