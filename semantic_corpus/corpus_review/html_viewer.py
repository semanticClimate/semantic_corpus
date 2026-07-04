"""HTML review viewer for interactive corpus paper selection."""

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from semantic_corpus.corpus_review.constants import (
    REVIEW_STATUS_EXCLUDE,
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
    REVIEW_TABLE_COLUMNS,
)
from semantic_corpus.corpus_review.interactive_review import (
    ReviewSession,
    ReviewSessionConfig,
)
from semantic_corpus.corpus_review.text_preview import strip_markup


def build_filter_summary(
    rows: List[Dict[str, Any]], config: ReviewSessionConfig, queue_indices: List[int]
) -> Dict[str, Any]:
    """Summarise how many papers match filters and score thresholds."""
    total = len(rows)
    score_distribution = dict(sorted(Counter(int(r.get("score") or 0) for r in rows).items()))
    status_counts = Counter(r.get("review_status", REVIEW_STATUS_REVIEW) for r in rows)

    messages: List[str] = [f"{total} papers in review table"]
    if config.min_score is not None:
        count = sum(1 for row in rows if int(row.get("score") or 0) >= config.min_score)
        messages.append(
            f"only {count} paper{'s' if count != 1 else ''} "
            f"{'reach' if count != 1 else 'reaches'} min_score >= {config.min_score}"
        )
        headline = (
            f"Only {count} paper{'s' if count != 1 else ''} "
            f"{'reach' if count != 1 else 'reaches'} "
            f"min_score >= {config.min_score} (of {total} total)"
        )
    else:
        headline = messages[0]
    if config.max_score is not None:
        count = sum(1 for row in rows if int(row.get("score") or 0) <= config.max_score)
        messages.append(
            f"{count} paper{'s' if count != 1 else ''} "
            f"{'have' if count != 1 else 'has'} max_score <= {config.max_score}"
        )
    if config.topic_filter:
        topic = config.topic_filter
        count = sum(
            1
            for row in rows
            if topic.lower()
            in " ".join(
                str(row.get(column) or "")
                for column in (
                    "location_terms",
                    "pollutant_terms",
                    "health_terms",
                    "cluster_terms",
                    "encyclopedia_category",
                    "title",
                    "abstract_snippet",
                )
            ).lower()
        )
        messages.append(
            f"{count} paper{'s' if count != 1 else ''} match topic {topic!r}"
        )
    if config.status_filter != "all":
        messages.append(f"status filter: {config.status_filter}")

    queue_count = len(queue_indices)
    messages.append(
        f"{queue_count} paper{'s' if queue_count != 1 else ''} in review queue"
    )

    return {
        "total": total,
        "queue_count": queue_count,
        "score_distribution": score_distribution,
        "status_counts": dict(status_counts),
        "filters": {
            "min_score": config.min_score,
            "max_score": config.max_score,
            "status": config.status_filter,
            "topic": config.topic_filter,
            "redo": config.redo,
        },
        "messages": messages,
        "headline": headline if config.min_score is not None else messages[0],
    }


def build_viewer_payload(session: ReviewSession) -> Dict[str, Any]:
    """Build JSON payload embedded in the HTML viewer.

    Only review-table metadata is embedded. Abstract, intro, and full text are
    fetched on demand from ``/api/paper-preview`` so papers are not copied
    into the HTML file.
    """
    papers: List[Dict[str, Any]] = []
    for index, row in enumerate(session.rows):
        entry = dict(row)
        entry.update(
            {
                "index": index,
                "in_queue": index in session.queue_indices,
                "title_plain": strip_markup(row.get("title") or ""),
            }
        )
        papers.append(entry)

    return {
        "papers": papers,
        "queue_indices": session.queue_indices,
        "summary": session.summary(),
        "filter_summary": build_filter_summary(
            session.rows, session.config, session.queue_indices
        ),
        "review_table_path": str(session.config.review_table_path),
        "review_table_columns": list(REVIEW_TABLE_COLUMNS),
    }


_VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Corpus review — paper by paper</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #52606d;
      --border: #d9e2ec;
      --include: #047857;
      --exclude: #b91c1c;
      --review: #b45309;
      --accent: #2563eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      background: #102a43;
      color: #fff;
      padding: 1rem 1.25rem;
    }
    header h1 {
      margin: 0 0 0.35rem;
      font-size: 1.35rem;
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    .headline {
      font-size: 1.05rem;
      color: #f0f4f8;
      margin-bottom: 0.75rem;
    }
    .stats {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.92rem;
    }
    .stat {
      background: rgba(255,255,255,0.12);
      border-radius: 999px;
      padding: 0.35rem 0.75rem;
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 1rem;
      padding: 1rem;
      min-height: calc(100vh - 120px);
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }
    .sidebar {
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 140px);
    }
    .sidebar-head, .paper-head {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border);
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    .filters {
      display: grid;
      gap: 0.5rem;
      padding: 0.85rem 1rem;
      border-bottom: 1px solid var(--border);
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.9rem;
    }
    .filters label { display: grid; gap: 0.2rem; }
    .filters input, .filters select, textarea, button {
      font: inherit;
    }
    .paper-list {
      overflow: auto;
      flex: 1;
    }
    .paper-item {
      display: block;
      width: 100%;
      text-align: left;
      border: 0;
      border-bottom: 1px solid var(--border);
      background: #fff;
      padding: 0.75rem 1rem;
      cursor: pointer;
    }
    .paper-item.active { background: #eff6ff; }
    .paper-item .title {
      font-size: 0.95rem;
      margin-bottom: 0.25rem;
    }
    .paper-item .meta {
      font-size: 0.8rem;
      color: var(--muted);
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    .status-include { color: var(--include); }
    .status-exclude { color: var(--exclude); }
    .status-review { color: var(--review); }
    .paper-body { padding: 1rem 1.25rem 1.5rem; }
    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1rem;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.85rem;
    }
    .badge {
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 0.2rem 0.55rem;
      background: #f8fafc;
    }
    h2 {
      margin: 0 0 0.75rem;
      line-height: 1.35;
      font-size: 1.45rem;
    }
    .section { margin-top: 1.25rem; }
    .section h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
      font-family: "Segoe UI", system-ui, sans-serif;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .section p {
      margin: 0;
      line-height: 1.55;
      white-space: pre-wrap;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 1.25rem;
      align-items: center;
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 0.65rem 1rem;
      cursor: pointer;
    }
    .btn-include { background: var(--include); color: #fff; }
    .btn-exclude { background: var(--exclude); color: #fff; }
    .btn-skip { background: #475569; color: #fff; }
    .btn-save { background: var(--accent); color: #fff; }
    .btn-nav { background: #e2e8f0; color: var(--text); }
    textarea {
      width: 100%;
      min-height: 70px;
      margin-top: 0.75rem;
      padding: 0.65rem;
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .score-bar {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
      margin-top: 0.5rem;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.85rem;
    }
    .paper-links {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 0.75rem 0 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.9rem;
    }
    .paper-links a {
      color: var(--accent);
    }
    .preview-loading { color: var(--muted); font-style: italic; }
    .score-chip {
      background: #eef2ff;
      border-radius: 6px;
      padding: 0.25rem 0.5rem;
    }
    .message {
      margin: 0.75rem 1rem 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: 0.9rem;
      color: var(--muted);
    }
    .empty-state {
      padding: 1.25rem;
      color: var(--muted);
      font-family: "Segoe UI", system-ui, sans-serif;
      line-height: 1.5;
    }
    @media (max-width: 900px) {
      .layout { grid-template-columns: 1fr; }
      .sidebar { max-height: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Corpus review — one paper at a time</h1>
    <div class="headline" id="headline"></div>
    <div class="stats" id="stats"></div>
  </header>
  <div class="message" id="save-message"></div>
  <div class="layout">
    <section class="panel sidebar">
      <div class="sidebar-head">
        <strong>Papers</strong>
        <span id="queue-label"></span>
      </div>
      <div class="filters">
        <label>Status
          <select id="filter-status">
            <option value="review">review (undecided)</option>
            <option value="include">include</option>
            <option value="exclude">exclude</option>
            <option value="all">all</option>
          </select>
        </label>
        <label>Topic contains (optional)
          <input id="filter-topic" type="text" placeholder="climate, health, ..." />
        </label>
      </div>
      <div class="paper-list" id="paper-list"></div>
    </section>
    <section class="panel">
      <div class="paper-head" id="paper-progress"></div>
      <div class="paper-body" id="paper-body"></div>
    </section>
  </div>
  <script>
    const payload = __PAYLOAD__;
    let papers = payload.papers;
    let queueIndices = [];
    let queuePosition = 0;
    let currentIndex = null;

    function statusClass(status) {
      return `status-${status}`;
    }

    function topicMatches(paper, topic) {
      if (!topic) return true;
      const haystack = [
        paper.topics, paper.location_terms, paper.pollutant_terms,
        paper.health_terms, paper.title, paper.abstract
      ].join(" ").toLowerCase();
      return haystack.includes(topic.toLowerCase());
    }

    function computeQueueIndices() {
      const status = document.getElementById("filter-status").value;
      const topic = document.getElementById("filter-topic").value.trim();
      const indices = [];
      papers.forEach((paper, index) => {
        if (status !== "all" && paper.review_status !== status) return;
        if (!topicMatches(paper, topic)) return;
        indices.push(index);
      });
      indices.sort((a, b) =>
        (papers[a].title_plain || papers[a].title || "")
          .localeCompare(papers[b].title_plain || papers[b].title || "")
      );
      return indices;
    }

    function emptyStateMessage() {
      if (!papers.length) {
        return (
          "This review table has no papers. " +
          "Run build_review_table.py or open the correct review_viewer.html."
        );
      }
      const status = document.getElementById("filter-status").value;
      if (status === "review") {
        return (
          "No undecided papers left. Set Status to \"include\", \"exclude\", or \"all\" " +
          "to inspect papers you already decided."
        );
      }
      return "No papers match the current filters. Try Status \"all\" or clear Topic.";
    }

    function updateSummary() {
      queueIndices = computeQueueIndices();
      if (queueIndices.length === 0) {
        currentIndex = null;
        queuePosition = 0;
      } else {
        if (queuePosition >= queueIndices.length) {
          queuePosition = queueIndices.length - 1;
        }
        currentIndex = queueIndices[queuePosition];
      }

      const total = papers.length;
      document.getElementById("headline").textContent =
        `${total} papers in review table · ${queueIndices.length} shown in queue`;

      const summary = { include: 0, review: 0, exclude: 0 };
      papers.forEach(p => { summary[p.review_status] = (summary[p.review_status] || 0) + 1; });
      document.getElementById("stats").innerHTML = [
        `<span class="stat">${queueIndices.length} in queue</span>`,
        `<span class="stat">include ${summary.include || 0}</span>`,
        `<span class="stat">review ${summary.review || 0}</span>`,
        `<span class="stat">exclude ${summary.exclude || 0}</span>`
      ].join("");

      document.getElementById("queue-label").textContent =
        ` (${queueIndices.length} shown)`;
      renderList();
      renderPaper();
    }

    function renderList() {
      const list = document.getElementById("paper-list");
      list.innerHTML = "";
      queueIndices.forEach((index, position) => {
        const paper = papers[index];
        const btn = document.createElement("button");
        btn.className = "paper-item" + (index === currentIndex ? " active" : "");
        btn.innerHTML = `
          <div class="title">${escapeHtml(paper.title_plain || paper.title || "(no title)")}</div>
          <div class="meta">
            <span class="${statusClass(paper.review_status)}">${paper.review_status}</span>
            · ${escapeHtml(paper.pmcid || paper.paper_id)}
          </div>`;
        btn.onclick = () => {
          currentIndex = index;
          queuePosition = position;
          renderList();
          renderPaper();
        };
        list.appendChild(btn);
      });
    }

    function renderPaper() {
      if (!queueIndices.length || currentIndex === null) {
        document.getElementById("paper-progress").textContent = "No papers in queue";
        document.getElementById("paper-body").innerHTML =
          `<div class="empty-state">${escapeHtml(emptyStateMessage())}</div>`;
        return;
      }
      const paper = papers[currentIndex];
      if (!paper) {
        document.getElementById("paper-progress").textContent = "No papers in queue";
        document.getElementById("paper-body").innerHTML = "";
        return;
      }
      document.getElementById("paper-progress").textContent =
        `Paper ${queuePosition + 1} of ${queueIndices.length} in queue`;

      const badges = [
        paper.review_status,
        paper.has_xml ? "XML" : null,
        paper.has_pdf ? "PDF" : null,
        paper.pmcid || null,
        paper.doi || null,
      ].filter(Boolean).map(text => `<span class="badge">${escapeHtml(text)}</span>`).join("");

      const paperLinks = [];
      if (paper.pmcid && paper.has_pdf) {
        paperLinks.push(`<a href="/papers/${encodeURIComponent(paper.pmcid)}.pdf" target="_blank" rel="noopener">Open PDF</a>`);
      }

      document.getElementById("paper-body").innerHTML = `
        <div class="badge-row">${badges}</div>
        <h2>${escapeHtml(paper.title_plain || paper.title || "(no title)")}</h2>
        <p><strong>Authors:</strong> ${escapeHtml(paper.authors || "")}</p>
        <p><strong>Journal:</strong> ${escapeHtml(paper.journal || "")}
           · <strong>Date:</strong> ${escapeHtml(paper.publication_date || "")}</p>
        <div class="paper-links" id="paper-links">${paperLinks.join(" · ")}</div>
        <div class="section"><h3>Abstract</h3><p id="preview-abstract" class="preview-loading">Loading preview…</p></div>
        <div class="section" id="intro-section" hidden><h3>Introduction</h3><p id="preview-intro"></p></div>
        <label><strong>Review note</strong>
          <textarea id="review-note">${escapeHtml(paper.review_notes || "")}</textarea>
        </label>
        <div class="actions">
          <button class="btn-include" onclick="decide('include')">Include (Y)</button>
          <button class="btn-exclude" onclick="decide('exclude')">Exclude (N)</button>
          <button class="btn-skip" onclick="decide('review', true)">Skip (S)</button>
          <button class="btn-nav" onclick="navigate(-1)">Previous</button>
          <button class="btn-nav" onclick="navigate(1)">Next</button>
          <button class="btn-save" onclick="saveRows()">Save review table</button>
        </div>`;
      loadPaperPreview(paper.index);
    }

    async function loadPaperPreview(index) {
      const abstractEl = document.getElementById("preview-abstract");
      const introSection = document.getElementById("intro-section");
      const introEl = document.getElementById("preview-intro");
      if (!abstractEl) return;
      try {
        const response = await fetch(`/api/paper-preview?index=${index}`);
        if (!response.ok) throw new Error("preview unavailable");
        const preview = await response.json();
        abstractEl.textContent = preview.abstract || papers[index].abstract_snippet || "No abstract available.";
        abstractEl.classList.remove("preview-loading");
        if (preview.intro && introEl && introSection) {
          introEl.textContent = preview.intro;
          introSection.hidden = false;
        }
        const linksEl = document.getElementById("paper-links");
        if (linksEl) {
          const links = [];
          if (preview.pdf_url) links.push(`<a href="${preview.pdf_url}" target="_blank" rel="noopener">Open PDF</a>`);
          if (preview.html_url) links.push(`<a href="${preview.html_url}" target="_blank" rel="noopener">Open HTML</a>`);
          if (links.length) linksEl.innerHTML = links.join(" · ");
        }
      } catch (err) {
        abstractEl.textContent = papers[index].abstract_snippet || "No abstract available.";
        abstractEl.classList.remove("preview-loading");
      }
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function decide(status, advance = false) {
      if (currentIndex === null || !queueIndices.length) return;
      const paper = papers[currentIndex];
      const note = document.getElementById("review-note");
      if (note) paper.review_notes = note.value.trim();
      paper.review_status = status;

      updateSummary();

      if (!queueIndices.length) {
        return;
      }
      if (advance || status === "review") {
        queuePosition = Math.min(queuePosition + 1, queueIndices.length - 1);
      } else {
        queuePosition = Math.min(queuePosition, queueIndices.length - 1);
      }
      currentIndex = queueIndices[queuePosition];
      renderList();
      renderPaper();
    }

    function navigate(delta) {
      queuePosition = Math.min(Math.max(0, queuePosition + delta), Math.max(0, queueIndices.length - 1));
      currentIndex = queueIndices[queuePosition];
      renderList();
      renderPaper();
    }

    async function saveRows() {
      const columns = payload.review_table_columns || [];
      const rows = papers.map(paper => {
        const row = {};
        columns.forEach(col => { row[col] = paper[col] ?? ""; });
        if (paper.abstract) {
          row.abstract_snippet = paper.abstract.slice(0, 200) +
            (paper.abstract.length > 200 ? "..." : "");
        }
        return row;
      });
      const message = document.getElementById("save-message");
      try {
        const response = await fetch("/api/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rows }),
        });
        if (!response.ok) throw new Error(await response.text());
        message.textContent = "Saved review_table.json, .csv, and .md";
      } catch (err) {
        message.textContent = "Save failed: " + err.message;
      }
    }

    document.querySelectorAll(".filters input, .filters select").forEach(el => {
      el.addEventListener("input", updateSummary);
      el.addEventListener("change", updateSummary);
    });

    document.addEventListener("keydown", (event) => {
      if (event.target.tagName === "TEXTAREA" || event.target.tagName === "INPUT") return;
      if (event.key === "y" || event.key === "Y") decide("include");
      if (event.key === "n" || event.key === "N") decide("exclude");
      if (event.key === "s" || event.key === "S") decide("review", true);
      if (event.key === "ArrowRight") navigate(1);
      if (event.key === "ArrowLeft") navigate(-1);
    });

    (function initFilters() {
      const filters = payload.filter_summary.filters || {};
      document.getElementById("filter-status").value = filters.status || "review";
      if (filters.topic) document.getElementById("filter-topic").value = filters.topic;
      updateSummary();
    })();
  </script>
</body>
</html>
"""


def render_review_viewer_html(payload: Dict[str, Any]) -> str:
    """Render standalone HTML with embedded JSON payload."""
    embedded = json.dumps(payload, ensure_ascii=False)
    embedded = embedded.replace("</", "<\\/")
    return _VIEWER_HTML.replace("__PAYLOAD__", embedded)


def write_review_viewer(config: ReviewSessionConfig, output_path: Path) -> Path:
    """Build and write the HTML review viewer."""
    session = ReviewSession.load(config)
    payload = build_viewer_payload(session)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_review_viewer_html(payload), encoding="utf-8")
    return output_path
