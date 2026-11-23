# Layout specimen — markers and omissions

**Purpose:** Small multi-format fixtures that encode conversion hard cases for Stage A/B input adapters.  
**Dir:** `tests/resources/input_adapters/`  
**Design:** [`semantic_corpus/corpus/docs/input_adapters.md`](../../../semantic_corpus/corpus/docs/input_adapters.md)  
**Priority review:** 2026-11-23 (team comments)

## Required markers (must survive conversion / appear in text)

| Marker / content | Feature |
|------------------|---------|
| `SPECIMEN_START_PAGE` | First page body |
| `SPECIMEN_END_PAGE` | Last page body |
| `SPECIMEN_RECTO` | Odd / right-hand page |
| `SPECIMEN_VERSO` | Even / left-hand page |
| `RUNNING_TITLE_CLIMATE` | Running title in header |
| `HEADER_PAGE_` + N | Header with page number |
| `FOOTER_PAGE_` + N | Footer with page number |
| `FLOAT_FIGURE_CAP` | Figure float caption |
| `FLOAT_TABLE_CAP` | Table float caption |
| `FLOAT_TEXTBOX` | Text float / sidebar |
| `FONT_BOLD` | Bold run |
| `FONT_ITALIC` | Italic run |
| `FONT_LARGE` | Larger font size |
| `café` / `Zürich` / `São` | Latin diacritics |
| `αβγ` / `ΔΩθ` | Greek |
| `नमस्ते` | Simple Devanagari |

## Files

| File | Role |
|------|------|
| `layout_specimen.html` | Messy HTML with page/recto-verso/header/footer/floats |
| `layout_specimen.jats.xml` | Mini JATS with same markers |
| `layout_specimen.txt` | Raw text (no coords) |
| `layout_specimen.md` | Markdown |
| `layout_specimen.hocr.html` | hOCR-ish with bbox titles |
| `layout_specimen.pdf` | Multi-page text-layer PDF (built by script) |
| `build_layout_specimen_pdf.py` | Regenerates the PDF with PyMuPDF |

---

## Omission priorities (from review)

### Critical (plan fixtures + adapter behaviour soon)

| Item | Note |
|------|------|
| **Multi-column** | STM default; naive top-to-bottom reading merges columns |
| **Footnotes / endnotes** | Must be distinct `text_block` kinds (or linked), not body prose |
| **Hyphenation / ligatures** | Rejoin `cli-`+`mate`; expand ﬁ/ﬂ so search and phrases work |

### Important (needed for trustworthy layout)

| Item | Note |
|------|------|
| **Rotated text** | Landscape tables, spine titles; coords/orientation matter |
| **Drop caps** | Leading oversized letter must join the paragraph, not a lone block |
| **Nested lists** | Preserve parentage among `listitem` blocks |
| **Cross-page floats** | One figure/table logical unit across page breaks |
| **Colour-only emphasis** | Red/blue spans with no bold/italic — still mark emphasis if possible |
| **Caption above vs below** | Ordering relative to the float body |

### Defer

| Item | Note |
|------|------|
| **Math** | MathML / equation images — later |
| **Complex tables** | Row/col spans beyond caption-as-block — later |

### Ignore (out of scope for now)

| Item | Note |
|------|------|
| **RTL / CJK** | Not important for current corpora |
| **Watermarks** | Ignore |
| **Devanagari ZWJ shaping** | Ignore beyond simple `नमस्ते` |

### Explain (keep on radar)

#### Wrong reading order

PDFs and some HTML do not store text in the order a human reads.

- **PDF:** operators may paint column 2 before column 1, or paint the float caption before the body that precedes it visually. Extractors that follow content-stream order then emit scrambled paragraphs.  
- **HTML:** `position: absolute` / CSS grid can place boxes so **DOM order ≠ visual order**.

Adapters must prefer **geometry-aware order** (top→bottom, left→right within columns) or tagged PDF/structure trees when present—not raw paint/DOM order. Multi-column makes this acute (hence critical).

**Fixture idea later:** two-column page where stream order is right-column-first; assert Stage A emits left column then right.

#### PDF crop box vs media box

A PDF page has several rectangles ([PDF boxes](https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf) §14.11.2 style):

| Box | Role |
|-----|------|
| **MediaBox** | Full page canvas (often including printer marks) |
| **CropBox** | Visible region when displayed/printed (viewer “page”) |
| **TrimBox / BleedBox** | Production trim / bleed (publishing) |

Text and image **coordinates** are usually in the media space. If we keep bboxes but interpret them against the wrong box, headers look shifted, “page 1” clips content, or OCR overlays miss glyphs. Adapters that preserve coordinates should record **which box** was used and normalise bboxes into a single page space (typically CropBox-relative).

**Priority:** important once we rely on coordinates; less urgent for text-only extract without bbox.

---

## Suggested next specimen increments

1. Two-column page (critical)  
2. Footnote + body with shared marker ids (critical)  
3. Soft hyphen / ligature line break (critical)  
4. Drop cap paragraph; nested `ul`/`ol`; caption-above figure; rotated label (important)

---

## OSS libraries vs omissions (check, late 2025 / 2026)

Your earlier finding still largely holds: **no single open library cleanly solves the critical set** (especially **true footnote semantics**). What changed is better *partial* coverage and clearer recipes.

| Need | Better than ~2023? | Libraries / notes |
|------|--------------------|-------------------|
| **Multi-column / reading order** | Yes, partial | **Docling** (layout + reading-order post-process; already in repo); **MinerU**; **pdfminer.six** LAParams; **pdfplumber** column-crop recipes; **pdftotext++** (Freiburg) natural reading order; **paperlayer** (claims column-first) |
| **Hyphenation / ligatures** | Yes, some | **pdftotext++** (explicit hyphen merge + ligature split); custom post-rules still common; Docling/MinerU help unevenly |
| **Footnotes as footnotes** | Still weak | 2025 parser benchmarks: tools either **drop** notes, or emit them as **normal body text** — almost none keep footnote/footer *roles*. **pdftotext++** advertises semantic roles including footnote; **paperlayer** claims reattach-to-anchor. Treat as **evaluate**, not solved |
| **Crop vs media box** | Yes (plumbing) | **pdfplumber** exposes mediabox/cropbox/trimbox and crop helpers; **PyMuPDF** page cropbox APIs. Easy to adopt in Stage A |
| **Rotated text** | Partial | PyMuPDF / pdfminer expose transform matrices; layout models may still mangle vertical/rotated runs — need targeted tests |
| **Drop caps / nested lists / caption side / colour emphasis / cross-page floats** | Mostly DIY | List nesting OK in HTML/JATS paths; PDF→structure still heuristic. Colour-only emphasis rarely preserved as “emphasis”. Cross-page floats remain hard |
| **Math / complex tables** | Improved but deferred OK | Docling TableFormer; MinerU tables — good enough to revisit when we un-defer |

**Recommendation for us:** keep **Docling** as default structured PDF→HTML; add **pdfplumber** (or PyMuPDF) for **cropbox-normalised coords** and column experiments; trial **pdftotext++** / **paperlayer** on footnote+hyphen fixtures before writing our own. Expect to own Stage B rules for footnote kinds, de-hyphenation fallbacks, and caption/float linking — libraries assist, they do not replace the contract.
