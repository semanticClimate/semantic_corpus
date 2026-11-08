"""Novice-friendly Europe PMC preflight check (run before collect)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Optional, TextIO

import requests

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.repositories.europe_pmc import (
    SEARCH_TIMEOUT_SECONDS,
    http_status_from_error_body,
    looks_like_fulltext_xml,
)

# Stable open-access article used only to probe fullTextXML health.
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
    name: str
    ok: bool
    status_code: Optional[int]
    guide: StatusGuide
    detail: str = ""


@dataclass
class EpmcDiagnostic:
    probes: List[ProbeResult]
    ok: bool

    @property
    def blocking(self) -> List[ProbeResult]:
        return [p for p in self.probes if p.guide.severity == "fail"]


class EpmcUnavailable(CorpusError):
    """Europe PMC preflight failed; message is already shown to the user."""


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
            advice="Safe to start the job.",
            severity="ok",
        )
    if code == 401:
        return StatusGuide(
            code_label="401",
            meaning="unauthorized (unusual for public Europe PMC)",
            advice="Retry later; if it persists, Europe PMC auth may have changed.",
            severity="fail",
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
            advice="Skip that paper or try again later; other papers may still work.",
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
            advice="Come back later and retry.",
            severity="fail",
        )
    if code == 502:
        return StatusGuide(
            code_label="502",
            meaning="bad gateway — Europe PMC or a proxy failed",
            advice="Come back later and retry.",
            severity="fail",
        )
    if code == 503:
        return StatusGuide(
            code_label="503",
            meaning="Europe PMC temporarily unavailable",
            advice="Come back later and retry.",
            severity="fail",
        )
    if code == 504:
        return StatusGuide(
            code_label="504",
            meaning="gateway timeout — Europe PMC too slow",
            advice="Come back later and retry.",
            severity="fail",
        )
    if code >= 500:
        return StatusGuide(
            code_label=str(code),
            meaning="server error on Europe PMC",
            advice="Come back later and retry.",
            severity="fail",
        )
    if code >= 400:
        return StatusGuide(
            code_label=str(code),
            meaning=f"HTTP error talking to Europe PMC",
            advice="Retry later. If it keeps happening, check query and network.",
            severity="fail",
        )
    return StatusGuide(
        code_label=str(code),
        meaning=f"unexpected HTTP status {code}",
        advice="Retry later.",
        severity="warn",
    )


def _probe_search() -> ProbeResult:
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
        guide = explain_status(None, kind="timeout")
        return ProbeResult("search", False, None, guide)
    except requests.RequestException:
        guide = explain_status(None, kind="connection")
        return ProbeResult("search", False, None, guide)

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
                meaning="search returned invalid data",
                advice="Come back later and retry.",
                severity="fail",
            )
    return ProbeResult("search", ok, code, guide)


def _probe_fulltext_xml(pmcid: str = _PROBE_PMCID) -> ProbeResult:
    url = f"{_BASE}/{pmcid}/fullTextXML"
    try:
        response = requests.get(url, timeout=_TIMEOUT)
    except requests.Timeout:
        guide = explain_status(None, kind="timeout")
        return ProbeResult("fulltext_xml", False, None, guide)
    except requests.RequestException:
        guide = explain_status(None, kind="connection")
        return ProbeResult("fulltext_xml", False, None, guide)

    code = response.status_code
    content = response.content or b""
    if code >= 400:
        guide = explain_status(code)
        return ProbeResult("fulltext_xml", False, code, guide)

    if not looks_like_fulltext_xml(content):
        stub = http_status_from_error_body(content)
        effective = stub or 500
        guide = explain_status(effective)
        return ProbeResult("fulltext_xml", False, effective, guide)

    guide = explain_status(code)
    return ProbeResult("fulltext_xml", True, code, guide)


def run_epmc_diagnostic() -> EpmcDiagnostic:
    """Probe Europe PMC search + full-text XML and return structured results."""
    probes = [_probe_search(), _probe_fulltext_xml()]
    ok = all(p.ok for p in probes)
    return EpmcDiagnostic(probes=probes, ok=ok)


def format_epmc_diagnostic(diag: EpmcDiagnostic) -> str:
    """Compact multi-line report for terminals."""
    lines: List[str] = ["┌─ Europe PMC check"]
    for probe in diag.probes:
        label = "Search API" if probe.name == "search" else "Full-text XML"
        if probe.ok:
            lines.append(f"│ {label:<14} OK")
        else:
            g = probe.guide
            lines.append(f"│ {label:<14} {g.code_label} — {g.meaning}")
            lines.append(f"│                → {g.advice}")

    lines.append("│")
    if diag.ok:
        lines.append("│ Ready — starting collect.")
    else:
        lines.append("│ Stopped before collect.")
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
) -> EpmcDiagnostic:
    """Run the diagnostic in front of a job; optionally abort on failure."""
    diag = print_epmc_diagnostic(stream=stream)
    if abort and not diag.ok:
        worst = diag.blocking[0] if diag.blocking else diag.probes[-1]
        # Short raise — the panel already explained; callers should not dump a traceback.
        raise EpmcUnavailable(
            f"Europe PMC unavailable ({worst.guide.code_label}). "
            f"{worst.guide.advice}"
        )
    return diag


def short_status_blurb(status_code: int) -> str:
    """One-line blurb for status lines (e.g. fail breakdown help)."""
    guide = explain_status(status_code)
    return f"{guide.code_label} — {guide.meaning}. {guide.advice}"
