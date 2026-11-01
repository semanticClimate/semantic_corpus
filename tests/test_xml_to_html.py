"""Tests for JATS/PMC XML → HTML conversion."""

from __future__ import annotations

from pathlib import Path

from semantic_corpus.transformation.xml_to_html import convert_xml_to_html


def _write_mini_jats(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <journal-meta><journal-title>Test Journal</journal-title></journal-meta>
    <article-meta>
      <article-id pub-id-type="pmcid">PMC1</article-id>
      <article-id pub-id-type="doi">10.1000/test</article-id>
      <title-group><article-title>Sample title</article-title></title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Doe</surname><given-names>Jane</given-names></name>
          <xref ref-type="aff" rid="aff1">1</xref>
        </contrib>
        <contrib contrib-type="author">
          <name><surname>Smith</surname><given-names>John</given-names></name>
          <xref ref-type="aff" rid="aff1">1</xref>
        </contrib>
      </contrib-group>
      <aff id="aff1"><label>1</label>Example Institute</aff>
      <pub-date><day>1</day><month>2</month><year>2024</year></pub-date>
      <abstract>
        <p>Oxygen isotope (<sup>17</sup>Δ) and CO<sub>2</sub> rise.</p>
      </abstract>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Intro</title>
      <p>Ratio (<sup>231</sup>Pa/<sup>230</sup>Th) is preserved.</p>
    </sec>
  </body>
</article>
""",
        encoding="utf-8",
    )


def test_inline_sup_sub_not_concatenated(tmp_path: Path) -> None:
    xml_path = tmp_path / "paper.xml"
    html_path = tmp_path / "paper.html"
    _write_mini_jats(xml_path)
    convert_xml_to_html(xml_path, html_path)
    text = html_path.read_text(encoding="utf-8")
    assert "<sup>17</sup>Δ" in text
    assert "CO<sub>2</sub>" in text
    assert "<sup>231</sup>Pa/<sup>230</sup>Th" in text
    # Regression: tails must not pile up after all supers
    assert "<sup>17</sup><sup>231</sup>" not in text


def test_front_matter_authors_and_ids(tmp_path: Path) -> None:
    xml_path = tmp_path / "paper.xml"
    html_path = tmp_path / "paper.html"
    _write_mini_jats(xml_path)
    convert_xml_to_html(xml_path, html_path)
    text = html_path.read_text(encoding="utf-8")
    assert 'class="front-matter"' in text
    assert "Jane Doe" in text
    assert "John Smith" in text
    assert "Example Institute" in text
    assert "Test Journal" in text
    assert "DOI: 10.1000/test" in text
    assert "PMCID: PMC1" in text
