"""Extended test: OA academic PDF (input) vs HTML (ground truth) overlap.

Paper: Marchi et al. 2020 ClimateEU (PMC7719169), Scientific Data, CC-BY-4.0.
PDF and HTML may each contain chrome/adverts the other lacks; core scholarly
phrases should largely overlap after whitespace normalization.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from semantic_corpus.corpus.converters.html_to_semantic import html_file_to_semantic
from semantic_corpus.transformation.xml_to_html import convert_xml_to_html

PAIR = (
    Path(__file__).resolve().parent
    / "resources"
    / "input_adapters"
    / "oa_pdf_html_pair"
)


def _norm(text: str) -> str:
    text = text.replace("\u00ad", "").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def _html_plain(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
    return re.sub(r"<[^>]+>", " ", raw)


def _load_manifest() -> dict:
    return json.loads((PAIR / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pair_paths() -> dict:
    paths = {
        "pdf": PAIR / "ClimateEU_PMC7719169.pdf",
        "html": PAIR / "ClimateEU_PMC7719169.html",
        "jats": PAIR / "ClimateEU_PMC7719169.jats.xml",
        "manifest": PAIR / "manifest.json",
    }
    for key, path in paths.items():
        assert path.is_file(), f"missing {key}: {path}"
    return paths


def test_oa_pair_fixture_metadata(pair_paths: dict) -> None:
    meta = _load_manifest()
    assert meta["pmcid"] == "PMC7719169"
    assert meta["doi"] == "10.1038/s41597-020-00763-0"
    assert meta["license"].startswith("CC-BY")
    assert 4 <= meta["pdf_pages"] <= 10
    assert len(meta["core_phrases"]) >= 8


def test_pdf_page_count_in_range(pair_paths: dict) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open(pair_paths["pdf"])
    assert 4 <= doc.page_count <= 10
    assert doc.page_count == _load_manifest()["pdf_pages"]


def test_html_ground_truth_contains_core_phrases(pair_paths: dict) -> None:
    meta = _load_manifest()
    html = _norm(_html_plain(pair_paths["html"]))
    missing = [p for p in meta["core_phrases"] if _norm(p) not in html]
    assert not missing, f"HTML ground truth missing phrases: {missing}"


def test_pdf_extractor_recall_vs_html_core_phrases(pair_paths: dict) -> None:
    """PDF text should recover most HTML-grounded scholarly phrases (FN tolerated)."""
    pymupdf = pytest.importorskip("pymupdf")
    meta = _load_manifest()
    phrases = meta["core_phrases"]
    floor = float(meta.get("min_pdf_recall", 0.7))
    pdf_text = _norm(
        "\n".join(page.get_text() for page in pymupdf.open(pair_paths["pdf"]))
    )
    hits = [p for p in phrases if _norm(p) in pdf_text]
    recall = len(hits) / len(phrases)
    assert recall >= floor, (
        f"PDF recall {recall:.2f} < {floor:.2f}; "
        f"hits={len(hits)}/{len(phrases)} missing={ [p for p in phrases if p not in hits] }"
    )


def test_jats_to_html_sectioner_keeps_title_and_climateeu(pair_paths: dict, tmp_path: Path) -> None:
    """JATS → HTML → sectioner still surfaces core identity strings."""
    out = tmp_path / "climateeu.html"
    convert_xml_to_html(pair_paths["jats"], out)
    semantic = html_file_to_semantic(out, paper_id="PMC7719169")
    joined = "\n".join(b["text"] for b in semantic["blocks"])
    assert "ClimateEU" in joined
    assert "Europe" in joined
    assert semantic["blocks"], "expected text_blocks from sectioner"


def test_pdf_and_html_share_title_token(pair_paths: dict) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    pdf_text = "\n".join(page.get_text() for page in pymupdf.open(pair_paths["pdf"]))
    html = _html_plain(pair_paths["html"])
    assert "ClimateEU" in pdf_text and "ClimateEU" in html
