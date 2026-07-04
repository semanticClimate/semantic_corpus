"""Build and export corpus review tables for browsing."""

import csv
import html
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import REVIEW_TABLE_COLUMNS
from semantic_corpus.corpus_review.query_run import load_query_run_record
from semantic_corpus.corpus_review.relevance_scorer import score_paper_relevance
from semantic_corpus.corpus_review.review_schema import make_review_row
from semantic_corpus.repositories._ids import get_result_paper_id, sanitize_paper_id
from semantic_corpus.ingestion.pygetpapers_ingester import (
    _discover_paper_folders,
    _eupmc_json_to_raw_metadata,
)
from semantic_corpus.tools.metadata_processor import MetadataProcessor


def _paper_has_file(corpus_dir: Path, paper_id: str, ext: str) -> bool:
    sub = "xml" if ext == "xml" else "pdf"
    path = Path(corpus_dir, "data", "documents", sub, f"{paper_id}.{ext}")
    return path.is_file() and path.stat().st_size > 0


def build_review_rows_from_corpus(
    corpus: CorpusManager,
    *,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from an ingested BAGIT corpus."""
    if not corpus.use_bagit:
        raise CorpusError("Review table requires BAGIT corpus (use_bagit=True)")

    rows: List[Dict[str, Any]] = []
    for paper_id in sorted(corpus.list_papers()):
        metadata = corpus.get_paper_metadata(paper_id)
        has_xml = _paper_has_file(corpus.corpus_dir, paper_id, "xml")
        has_pdf = _paper_has_file(corpus.corpus_dir, paper_id, "pdf")
        score, matched = score_paper_relevance(
            metadata, has_xml=has_xml, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_xml,
                has_pdf=has_pdf,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def build_review_rows_from_pygetpapers(
    pygetpapers_dir: Path,
    *,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from raw pygetpapers output (before or without corpus ingest)."""
    pygetpapers_dir = Path(pygetpapers_dir)
    processor = MetadataProcessor()
    rows: List[Dict[str, Any]] = []

    for folder in _discover_paper_folders(pygetpapers_dir):
        json_path = Path(folder, "eupmc_result.json")
        with open(json_path, "r", encoding="utf-8") as handle:
            eupmc_data = json.load(handle)
        raw = _eupmc_json_to_raw_metadata(eupmc_data)
        metadata = processor.normalize_metadata(raw)
        paper_id = f"europe_pmc_{folder.name}"
        has_xml = Path(folder, "fulltext.xml").is_file()
        has_pdf = Path(folder, "fulltext.pdf").is_file()
        score, matched = score_paper_relevance(
            metadata, has_xml=has_xml, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_xml,
                has_pdf=has_pdf,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def _normalize_author_names(authors: Any) -> List[str]:
    """Flatten Europe PMC author entries (dicts or strings) into name strings."""
    if not authors:
        return []
    if isinstance(authors, str):
        return [authors]
    names: List[str] = []
    for author in authors:
        if isinstance(author, dict):
            name = (
                author.get("fullName")
                or author.get("lastName")
                or author.get("firstName")
                or ""
            )
            if name:
                names.append(str(name))
        elif author:
            names.append(str(author))
    return names


def build_review_rows_from_search_results(
    search_results_path: Path,
    *,
    xml_dir: Optional[Path] = None,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from a flat semantic_corpus search_results.json.

    Layout: search_results.json (list of paper dicts) plus optional sibling
    {pmcid}.xml / {pmcid}.pdf files (as produced by the download workflow).

    Args:
        search_results_path: Path to search_results.json.
        xml_dir: Directory holding {pmcid}.xml/.pdf; defaults to the JSON's folder.
        query_name: Query name for provenance columns.
        query_string: Query string for provenance columns.

    Returns:
        Review rows sorted by descending score.
    """
    search_results_path = Path(search_results_path)
    if not search_results_path.is_file():
        raise CorpusError(f"search_results.json not found: {search_results_path}")

    if xml_dir is None:
        xml_dir = search_results_path.parent
    xml_dir = Path(xml_dir)

    with open(search_results_path, "r", encoding="utf-8") as handle:
        results = json.load(handle)
    if not isinstance(results, list):
        raise CorpusError(
            f"search_results.json must contain a list, got {type(results).__name__}"
        )

    rows: List[Dict[str, Any]] = []
    for paper in results:
        pmcid = paper.get("pmcid") or ""
        pmid = paper.get("pmid") or ""
        file_id = sanitize_paper_id(get_result_paper_id(paper) or "")
        identifier = pmcid or pmid or file_id
        paper_id = f"europe_pmc_{identifier}" if pmcid else f"{paper.get('source_repository', 'paper')}_{identifier}"

        has_xml = bool(file_id) and Path(xml_dir, f"{file_id}.xml").is_file()
        has_html = bool(file_id) and Path(xml_dir, f"{file_id}.html").is_file()
        has_pdf = bool(file_id) and Path(xml_dir, f"{file_id}.pdf").is_file()
        has_fulltext = has_xml or has_html

        metadata = dict(paper)
        metadata["authors"] = _normalize_author_names(paper.get("authors"))

        score, matched = score_paper_relevance(
            metadata, has_xml=has_fulltext, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_fulltext,
                has_pdf=has_pdf,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def export_review_table_json(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return path


def export_review_table_csv(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REVIEW_TABLE_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in REVIEW_TABLE_COLUMNS})
    return path


def export_review_table_markdown(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Corpus review table",
        "",
        "| review_status | score | title | pmcid | has_xml | has_pdf |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        title = (row["title"] or "").replace("|", "\\|")[:80]
        lines.append(
            f"| {row['review_status']} | {row['score']} | {title} | "
            f"{row['pmcid']} | {row['has_xml']} | {row['has_pdf']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _default_review_table_css_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "review_table.css"


def _css_section(default_css: str, marker: str) -> str:
    """Return one marked section from the default stylesheet."""
    if marker not in default_css:
        return ""
    return marker + default_css.split(marker, 1)[1].split("\n\n/* ", 1)[0]


def ensure_review_table_css(output_dir: Path, basename: str = "review_table") -> Path:
    """Copy default CSS beside the HTML table if the user has not created one yet."""
    output_dir = Path(output_dir)
    css_path = output_dir / f"{basename}.css"
    default_css = _default_review_table_css_path().read_text(encoding="utf-8")
    if not css_path.is_file():
        css_path.write_text(default_css, encoding="utf-8")
        return css_path

    text = css_path.read_text(encoding="utf-8")
    if "/* reader panel *//* reader panel */" in text or text.count("/* reader panel */") > 1:
        css_path.write_text(default_css, encoding="utf-8")
        return css_path

    sections = (
        (".reader-body", "/* reader body */"),
    )
    appended = False
    for needle, marker in sections:
        if needle not in text and marker in default_css:
            section = _css_section(default_css, marker)
            if section:
                text = text.rstrip() + "\n\n" + section
                appended = True
    if appended:
        css_path.write_text(text, encoding="utf-8")
    return css_path


def export_review_table_html(
    rows: List[Dict[str, Any]], path: Path, *, css_href: str = "review_table.css"
) -> Path:
    """Export an editable HTML review table (styled via external CSS)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_review_table_css(path.parent, path.stem)

    include = sum(1 for row in rows if row.get("review_status") == "include")
    review = sum(1 for row in rows if row.get("review_status") == "review")
    exclude = sum(1 for row in rows if row.get("review_status") == "exclude")

    review_json = path.with_suffix(".json")
    query_dir = path.parent.parent
    serve_command = (
        f"./venv/bin/python scripts/review_viewer.py serve "
        f"--review-table {review_json} "
        f"--query-dir {query_dir}"
    )

    embedded = json.dumps(rows, ensure_ascii=False)
    embedded = embedded.replace("</", "<\\/")

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Corpus review table</title>
  <link rel="stylesheet" href="{html.escape(css_href)}" />
  <style>
    /* Critical reader layout — kept inline so papers always display */
    #paper-reader.open {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) min(52rem, 58vw);
      grid-template-rows: 1fr;
      height: 100vh;
      z-index: 1000;
    }}
    #paper-reader .reader-panel {{
      display: flex;
      flex-direction: column;
      min-height: 0;
      height: 100%;
    }}
    #paper-reader .reader-body {{
      flex: 1 1 0;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }}
    #paper-reader .reader-body iframe,
    #paper-reader .reader-body embed {{
      flex: 1 1 0;
      min-height: 0;
      width: 100%;
      border: 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Corpus review table</h1>
    <p class="summary">{len(rows)} papers · include {include} · review {review} · exclude {exclude}</p>
    <p id="connection-banner" class="connection-banner connection-banner--warn" hidden></p>
    <p class="toolbar">
      Edit <strong>Status</strong> and <strong>Notes</strong> below.
      Style this page via <code>{html.escape(css_href)}</code>.
      Full papers load only when this page is opened via <code>review_viewer.py serve</code> (http:// URL, not a saved file).
    </p>
  </header>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Status</th>
          <th>Title</th>
          <th>PMCID</th>
          <th>Authors</th>
          <th>Date</th>
          <th>XML</th>
          <th>PDF</th>
          <th>Read</th>
          <th>Abstract</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody id="review-body"></tbody>
    </table>
  </div>
  <div id="paper-reader" aria-hidden="true">
    <div class="reader-main" id="reader-backdrop"></div>
    <aside class="reader-panel" role="dialog" aria-label="Full paper">
      <div class="reader-head">
        <div class="reader-head-main">
          <h2 id="reader-title">Full paper</h2>
          <div class="reader-formats" id="reader-formats" hidden>
            <button type="button" class="format-btn" data-format="html">HTML</button>
            <button type="button" class="format-btn" data-format="pdf">PDF</button>
          </div>
        </div>
        <button type="button" id="reader-close">Close</button>
      </div>
      <div class="reader-body">
        <iframe id="paper-frame" title="Full paper (HTML)" hidden></iframe>
        <embed id="paper-embed" type="application/pdf" title="Full paper (PDF)" hidden />
        <p id="reader-status" class="reader-status" hidden></p>
      </div>
    </aside>
  </div>
  <p class="toolbar">
    <button id="save-btn" type="button">Save review table</button>
    <span id="save-message"></span>
  </p>
  <script>
    const rows = {embedded};
    let activePaperIndex = null;
    let paperFormats = {{ pdf_url: null, html_url: null }};
    let serveReady = false;
    let pdfBlobUrl = null;

    const SERVE_COMMAND = {json.dumps(serve_command)};

    function setConnectionBanner(message, ok = false) {{
      const banner = document.getElementById("connection-banner");
      if (!message) {{
        banner.hidden = true;
        banner.textContent = "";
        return;
      }}
      banner.hidden = false;
      banner.className = "connection-banner " + (ok ? "connection-banner--ok" : "connection-banner--warn");
      banner.innerHTML = message;
    }}

    async function checkServer() {{
      if (location.protocol === "file:") {{
        serveReady = false;
        setConnectionBanner(
          "You opened a saved file — papers cannot load this way. " +
          "Run <code>" + escapeHtml(SERVE_COMMAND) + "</code> " +
          "then open <code>http://127.0.0.1:8765/review_table.html</code> in your browser."
        );
        return false;
      }}
      try {{
        const response = await fetch("/api/health");
        if (!response.ok) throw new Error("health check failed");
        serveReady = true;
        setConnectionBanner(
          "Connected to review server at <code>" + escapeHtml(location.origin) + "</code>. " +
          "Click <strong>Read</strong> to open papers.",
          true
        );
        return true;
      }} catch (err) {{
        serveReady = false;
        setConnectionBanner(
          "Review server not running. Start it with <code>" + escapeHtml(SERVE_COMMAND) + "</code> " +
          "then open <code>http://127.0.0.1:8765/review_table.html</code> (not a file:// path)."
        );
        return false;
      }}
    }}

    function revokePdfBlob() {{
      if (pdfBlobUrl) {{
        URL.revokeObjectURL(pdfBlobUrl);
        pdfBlobUrl = null;
      }}
    }}

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function renderTable() {{
      const body = document.getElementById("review-body");
      body.innerHTML = rows.map((row, index) => `
        <tr data-index="${{index}}">
          <td>
            <select class="review-status" aria-label="Review status">
              <option value="review" ${{row.review_status === "review" ? "selected" : ""}}>review</option>
              <option value="include" ${{row.review_status === "include" ? "selected" : ""}}>include</option>
              <option value="exclude" ${{row.review_status === "exclude" ? "selected" : ""}}>exclude</option>
            </select>
          </td>
          <td class="col-title">${{escapeHtml(row.title)}}</td>
          <td>${{escapeHtml(row.pmcid)}}</td>
          <td>${{escapeHtml(row.authors)}}</td>
          <td>${{escapeHtml(row.publication_date)}}</td>
          <td>${{row.has_xml ? "yes" : "no"}}</td>
          <td>${{row.has_pdf ? "yes" : "no"}}</td>
          <td>
            <button type="button" class="btn-read" data-index="${{index}}"
              ${{row.pmcid ? "" : "disabled"}} aria-label="Read full paper">
              Read
            </button>
          </td>
          <td class="col-abstract">${{escapeHtml(row.abstract_snippet)}}</td>
          <td class="col-notes"><textarea class="review-notes" rows="3">${{escapeHtml(row.review_notes || "")}}</textarea></td>
        </tr>`).join("");
    }}

    function collectRows() {{
      return rows.map((row, index) => {{
        const tr = document.querySelector(`tr[data-index="${{index}}"]`);
        const status = tr.querySelector(".review-status").value;
        const notes = tr.querySelector(".review-notes").value.trim();
        return {{ ...row, review_status: status, review_notes: notes }};
      }});
    }}

    async function saveRows() {{
      const message = document.getElementById("save-message");
      const payload = {{ rows: collectRows() }};
      try {{
        const response = await fetch("/api/save", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});
        if (!response.ok) throw new Error(await response.text());
        message.textContent = "Saved review_table.json, .csv, .html, and .md";
      }} catch (err) {{
        const blob = new Blob([JSON.stringify(payload.rows, null, 2)], {{ type: "application/json" }});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "review_table.json";
        link.click();
        URL.revokeObjectURL(url);
        message.textContent = "Downloaded review_table.json (use serve mode to save in place)";
      }}
    }}

    function highlightRow(index) {{
      document.querySelectorAll("tr.row-reading").forEach((row) => {{
        row.classList.remove("row-reading");
      }});
      const row = document.querySelector(`tr[data-index="${{index}}"]`);
      if (!row) return;
      row.classList.add("row-reading");
      row.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
    }}

    function clearRowHighlight() {{
      document.querySelectorAll("tr.row-reading").forEach((row) => {{
        row.classList.remove("row-reading");
      }});
      activePaperIndex = null;
    }}

    function updateFormatButtons() {{
      const formatsEl = document.getElementById("reader-formats");
      const pdfBtn = formatsEl.querySelector('[data-format="pdf"]');
      const htmlBtn = formatsEl.querySelector('[data-format="html"]');
      pdfBtn.disabled = !paperFormats.pdf_url;
      htmlBtn.disabled = !paperFormats.html_url;
      formatsEl.hidden = !paperFormats.pdf_url && !paperFormats.html_url;
    }}

    function hideReaderStatus() {{
      const status = document.getElementById("reader-status");
      status.hidden = true;
      status.textContent = "";
    }}

    function showReaderStatus(message, isError = false) {{
      clearPaperViews();
      const status = document.getElementById("reader-status");
      status.textContent = message;
      status.className = "reader-status" + (isError ? " reader-status--error" : "");
      status.hidden = false;
    }}

    function clearPaperViews() {{
      const frame = document.getElementById("paper-frame");
      const embed = document.getElementById("paper-embed");
      frame.hidden = true;
      embed.hidden = true;
      frame.removeAttribute("srcdoc");
      frame.src = "about:blank";
      embed.removeAttribute("src");
      revokePdfBlob();
      hideReaderStatus();
    }}

    async function setPaperFormat(format) {{
      const url = format === "html" ? paperFormats.html_url : paperFormats.pdf_url;
      if (!url) return;
      if (!serveReady) {{
        showReaderStatus("Start the review server first (see the red banner above).", true);
        return;
      }}
      const frame = document.getElementById("paper-frame");
      const embed = document.getElementById("paper-embed");
      hideReaderStatus();
      revokePdfBlob();
      document.querySelectorAll(".format-btn").forEach((button) => {{
        button.classList.toggle("active", button.dataset.format === format);
        button.setAttribute("aria-pressed", button.dataset.format === format ? "true" : "false");
      }});
      try {{
        const response = await fetch(url);
        if (!response.ok) throw new Error("HTTP " + response.status);
        if (format === "html") {{
          embed.hidden = true;
          embed.removeAttribute("src");
          frame.hidden = false;
          frame.src = "about:blank";
          frame.srcdoc = await response.text();
        }} else {{
          frame.hidden = true;
          frame.removeAttribute("srcdoc");
          frame.src = "about:blank";
          const blob = await response.blob();
          pdfBlobUrl = URL.createObjectURL(blob);
          embed.hidden = false;
          embed.src = pdfBlobUrl;
        }}
      }} catch (err) {{
        showReaderStatus("Failed to load " + format.toUpperCase() + ": " + err.message, true);
      }}
    }}

    function showFrameMessage(message, isError = false) {{
      showReaderStatus(message, isError);
    }}

    async function openPaper(index) {{
      const row = rows[index];
      if (!row || !row.pmcid) return;

      highlightRow(index);
      activePaperIndex = index;

      const reader = document.getElementById("paper-reader");
      document.getElementById("reader-title").textContent = row.title || row.pmcid;
      clearPaperViews();
      reader.classList.add("open");
      reader.setAttribute("aria-hidden", "false");
      document.body.classList.add("reader-open");

      paperFormats = {{ pdf_url: null, html_url: null }};
      updateFormatButtons();

      if (!serveReady) {{
        await checkServer();
      }}
      if (!serveReady) {{
        showFrameMessage("Papers only load via the local server — see the banner above.", true);
        return;
      }}

      try {{
        const response = await fetch(`/api/paper-preview?index=${{index}}`);
        if (!response.ok) throw new Error("preview unavailable");
        const preview = await response.json();
        paperFormats = {{
          pdf_url: preview.pdf_url || null,
          html_url: preview.html_url || null,
        }};
        updateFormatButtons();
        if (paperFormats.pdf_url) {{
          await setPaperFormat("pdf");
        }} else if (paperFormats.html_url) {{
          await setPaperFormat("html");
        }} else {{
          showFrameMessage("No HTML or PDF available for this paper.", true);
        }}
      }} catch (err) {{
        showFrameMessage("Could not load paper: " + err.message, true);
      }}
    }}

    function closePaper() {{
      const reader = document.getElementById("paper-reader");
      reader.classList.remove("open");
      reader.setAttribute("aria-hidden", "true");
      document.body.classList.remove("reader-open");
      clearPaperViews();
      clearRowHighlight();
      paperFormats = {{ pdf_url: null, html_url: null }};
      document.getElementById("reader-formats").hidden = true;
    }}

    document.getElementById("save-btn").addEventListener("click", saveRows);
    document.getElementById("reader-close").addEventListener("click", closePaper);
    document.getElementById("reader-backdrop").addEventListener("click", closePaper);
    document.getElementById("reader-formats").addEventListener("click", async (event) => {{
      const button = event.target.closest(".format-btn");
      if (!button || button.disabled) return;
      await setPaperFormat(button.dataset.format);
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") closePaper();
    }});
    document.getElementById("review-body").addEventListener("click", (event) => {{
      const button = event.target.closest(".btn-read");
      if (!button || button.disabled) return;
      openPaper(Number(button.dataset.index));
    }});
    renderTable();
    checkServer();
  </script>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path


def export_review_tables(
    rows: List[Dict[str, Any]], output_dir: Path, basename: str = "review_table"
) -> Dict[str, Path]:
    """Export JSON, CSV, Markdown, and editable HTML review tables."""
    output_dir = Path(output_dir)
    html_path = Path(output_dir, f"{basename}.html")
    return {
        "json": export_review_table_json(
            rows, Path(output_dir, f"{basename}.json")
        ),
        "csv": export_review_table_csv(rows, Path(output_dir, f"{basename}.csv")),
        "markdown": export_review_table_markdown(
            rows, Path(output_dir, f"{basename}.md")
        ),
        "html": export_review_table_html(rows, html_path),
        "css": ensure_review_table_css(output_dir, basename),
    }


def load_query_context(query_run_path: Optional[Path]) -> Dict[str, str]:
    if not query_run_path or not Path(query_run_path).is_file():
        return {"query_name": "", "query_string": ""}
    record = load_query_run_record(query_run_path)
    return {
        "query_name": record.get("query_name") or "",
        "query_string": record.get("query_string") or "",
    }
