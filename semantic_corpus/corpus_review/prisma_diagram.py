"""Render PRISMA-like diagrams (Mermaid and Graphviz DOT) from prisma_flow."""

from pathlib import Path
from typing import Any, Dict, List

from semantic_corpus.corpus_review.constants import PRISMA_FLOW_BASENAME


def _escape_mermaid_label(text: str, max_len: int = 100) -> str:
    cleaned = (
        (text or "")
        .replace("\n", " ")
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
    )
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def _escape_dot_label(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')


def _download_status_lines(flow: Dict[str, Any]) -> List[str]:
    check = flow.get("download_check") or {}
    if not check:
        return []
    status = str(check.get("status") or "unknown")
    message = str(check.get("message") or "")
    lines = [
        f"status: {status}",
        (
            f"files present {check.get('n_present_files')}/"
            f"{check.get('n_expected_files')} "
            f"(formats {check.get('formats')})"
        ),
    ]
    if message:
        lines.append(message)
    return lines


def _artefact_lines(flow: Dict[str, Any], *, max_path: int = 72) -> List[str]:
    lines: List[str] = []
    for item in flow.get("artefacts") or []:
        role = str(item.get("role") or "")
        path = str(item.get("path") or "")
        note = str(item.get("note") or "")
        exists = item.get("exists")
        mark = "ok" if exists else "missing"
        if role == "raw_query":
            lines.append(f"raw_query: {note}")
            continue
        if not path and not note:
            continue
        label = path if path else note
        label = label if len(label) <= max_path else label[: max_path - 3] + "..."
        lines.append(f"{role} [{mark}]: {label}")
    return lines


def _provenance_short(flow: Dict[str, Any]) -> List[str]:
    prov = (flow.get("meta") or {}).get("count_provenance") or {}
    keys = (
        "n_identified",
        "n_retrieved",
        "n_with_fulltext",
        "n_screened",
    )
    lines = []
    for key in keys:
        value = prov.get(key)
        if value:
            lines.append(f"{key} <- {value}")
    return lines


def render_prisma_mermaid(flow: Dict[str, Any]) -> str:
    """Return Mermaid flowchart text for docs and previews."""
    meta = flow.get("meta") or {}
    counts = flow.get("counts") or {}
    exclusions: List[Dict[str, Any]] = flow.get("exclusions") or []

    query = _escape_mermaid_label(str(meta.get("query_string") or ""), max_len=120)
    repo = _escape_mermaid_label(str(meta.get("repository") or "unknown"))
    limit = meta.get("limit")
    limit_text = str(limit) if limit is not None else "n/a"
    dates = ""
    if meta.get("start_date") or meta.get("end_date"):
        dates = (
            f"<br/>dates: {meta.get('start_date') or '?'} → "
            f"{meta.get('end_date') or '?'}"
        )

    hitcount_note = (
        "hitCount override/API"
        if meta.get("identified_is_hitcount")
        else "NOT a database hitCount (equals retrieved)"
    )

    n_identified = counts.get("n_identified")
    n_retrieved = counts.get("n_retrieved")
    n_screened = counts.get("n_screened")
    n_include = counts.get("n_include")
    n_still_review = counts.get("n_still_review")
    n_exclude = counts.get("n_exclude")
    n_final = counts.get("n_final_table")
    n_fulltext = counts.get("n_with_fulltext")
    n_xml = counts.get("n_xml_on_disk")
    n_pdf = counts.get("n_pdf_on_disk")
    n_html = counts.get("n_html_on_disk")

    exclusion_lines = []
    for item in exclusions:
        reason = _escape_mermaid_label(str(item.get("reason") or ""))
        exclusion_lines.append(f"{reason}: {item.get('n', 0)}")
    if not exclusion_lines:
        exclusion_lines = ["none"]
    exclusion_block = "<br/>".join(exclusion_lines)

    artefact_block = "<br/>".join(
        _escape_mermaid_label(line, max_len=110) for line in _artefact_lines(flow)
    ) or "(no artefacts)"
    provenance_block = "<br/>".join(
        _escape_mermaid_label(line, max_len=110) for line in _provenance_short(flow)
    ) or "(none)"
    download_block = "<br/>".join(
        _escape_mermaid_label(line, max_len=140)
        for line in _download_status_lines(flow)
    ) or "download check not run"

    lines = [
        "flowchart TD",
        f'  ID["IDENTIFICATION<br/>repository: {repo}'
        f'<br/>raw query: {query}{dates}'
        f'<br/>limit: {limit_text}'
        f'<br/>records identified: {n_identified}'
        f'<br/>{hitcount_note}"]',
        f'  RET["RETRIEVED / DOWNLOAD CUTOFF'
        f'<br/>retrieved: {n_retrieved}'
        f'<br/>full text on disk: {n_fulltext}'
        f'<br/>xml={n_xml} pdf={n_pdf} html={n_html}"]',
        f'  DL["Download check<br/>{download_block}"]',
        f'  SCR["MANUAL FILTERING (eligibility)'
        f'<br/>screened: {n_screened}"]',
        f'  INC["FINAL TABLE'
        f'<br/>include: {n_include}'
        f'<br/>still review: {n_still_review}'
        f'<br/>exclude: {n_exclude}'
        f'<br/>final table rows: {n_final}"]',
        f'  EX["Exclusions<br/>{exclusion_block}"]',
        f'  ART["Local artefacts<br/>{artefact_block}"]',
        f'  PROV["Count sources<br/>{provenance_block}"]',
        "  ID --> RET",
        "  RET --> DL",
        "  DL --> SCR",
        "  SCR --> INC",
        "  RET -.-> EX",
        "  SCR -.-> EX",
        "  ID --- ART",
        "  INC --- PROV",
    ]
    return "\n".join(lines) + "\n"


def render_prisma_dot(flow: Dict[str, Any]) -> str:
    """Return Graphviz DOT for manuscript-friendly SVG/PNG via `dot`."""
    meta = flow.get("meta") or {}
    counts = flow.get("counts") or {}
    exclusions: List[Dict[str, Any]] = flow.get("exclusions") or []

    query = _escape_dot_label(str(meta.get("query_string") or ""))
    repo = _escape_dot_label(str(meta.get("repository") or "unknown"))
    limit = meta.get("limit")
    limit_text = str(limit) if limit is not None else "n/a"
    hitcount_note = (
        "hitCount from override/API"
        if meta.get("identified_is_hitcount")
        else "NOT database hitCount (= retrieved)"
    )

    exclusion_lines = [
        f"{item.get('reason')}: {item.get('n', 0)}" for item in exclusions
    ] or ["none"]
    exclusion_label = "\\n".join(_escape_dot_label(line) for line in exclusion_lines)
    artefact_label = "\\n".join(
        _escape_dot_label(line) for line in _artefact_lines(flow, max_path=64)
    ) or "(none)"
    provenance_label = "\\n".join(
        _escape_dot_label(line) for line in _provenance_short(flow)
    ) or "(none)"
    download_label = "\\n".join(
        _escape_dot_label(line) for line in _download_status_lines(flow)
    ) or "download check not run"

    return "\n".join(
        [
            "digraph prisma_flow {",
            "  rankdir=TB;",
            '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
            f'  ID [fillcolor="#e8f4fc", label="IDENTIFICATION\\n'
            f"repository: {repo}\\nraw query: {query}\\nlimit: {limit_text}\\n"
            f"records identified: {counts.get('n_identified')}\\n"
            f'{hitcount_note}"];',
            f'  RET [fillcolor="#eef9ee", label="RETRIEVED / DOWNLOAD CUTOFF\\n'
            f"retrieved: {counts.get('n_retrieved')}\\n"
            f"full text on disk: {counts.get('n_with_fulltext')}\\n"
            f"xml={counts.get('n_xml_on_disk')} "
            f"pdf={counts.get('n_pdf_on_disk')} "
            f'html={counts.get("n_html_on_disk")}"];',
            f'  DL [fillcolor="#ffe6e6", label="Download check\\n{download_label}"];',
            f'  SCR [fillcolor="#fff8e6", label="MANUAL FILTERING\\n'
            f'screened: {counts.get("n_screened")}"];',
            f'  INC [fillcolor="#e8f8e8", label="FINAL TABLE\\n'
            f"include: {counts.get('n_include')}\\n"
            f"still review: {counts.get('n_still_review')}\\n"
            f"exclude: {counts.get('n_exclude')}\\n"
            f'final table rows: {counts.get("n_final_table")}"];',
            f'  EX [fillcolor="#fdecea", label="Exclusions\\n{exclusion_label}"];',
            f'  ART [fillcolor="#f5f5f5", label="Local artefacts\\n{artefact_label}"];',
            f'  PROV [fillcolor="#f5f5f5", label="Count sources\\n{provenance_label}"];',
            "  ID -> RET;",
            "  RET -> DL;",
            "  DL -> SCR;",
            "  SCR -> INC;",
            '  RET -> EX [style=dashed];',
            '  SCR -> EX [style=dashed];',
            "  ID -> ART [style=dotted];",
            "  INC -> PROV [style=dotted];",
            "}",
            "",
        ]
    )


def write_prisma_diagrams(flow: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    """Write prisma_flow.mmd and prisma_flow.dot under output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "mermaid": Path(output_dir, f"{PRISMA_FLOW_BASENAME}.mmd"),
        "dot": Path(output_dir, f"{PRISMA_FLOW_BASENAME}.dot"),
    }
    paths["mermaid"].write_text(render_prisma_mermaid(flow), encoding="utf-8")
    paths["dot"].write_text(render_prisma_dot(flow), encoding="utf-8")
    return paths
