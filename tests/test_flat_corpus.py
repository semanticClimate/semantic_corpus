"""BagIt packets layout + collect resume helpers."""

from __future__ import annotations

import json
from pathlib import Path

from semantic_corpus.pipeline.flat_corpus import (
    ensure_light_bagit,
    packets_dir,
    paper_collect_done,
    paper_done_enough,
    paper_has_text,
    path_json,
    path_xml,
    write_json_atomic,
)


def test_ensure_light_bagit_and_packet_paths(tmp_path: Path):
    ensure_light_bagit(tmp_path)
    assert (tmp_path / "bagit.txt").is_file()
    assert packets_dir(tmp_path) == tmp_path / "data" / "packets"
    assert path_json(tmp_path, "PMC1") == tmp_path / "data" / "packets" / "PMC1.json"
    assert path_xml(tmp_path, "europe_pmc_PMC1") == (
        tmp_path / "data" / "packets" / "PMC1.xml"
    )


def test_collect_done_requires_xml_not_abstract_only(tmp_path: Path):
    ensure_light_bagit(tmp_path)
    write_json_atomic(
        path_json(tmp_path, "PMC9"),
        {"pmcid": "PMC9", "abstract": "Only abstract"},
    )
    assert paper_has_text(tmp_path, "PMC9")
    assert not paper_collect_done(tmp_path, "PMC9")
    assert not paper_done_enough(tmp_path, "PMC9")

    path_xml(tmp_path, "PMC9").write_bytes(
        b'<?xml version="1.0"?><article><body><p>x</p></body></article>'
    )
    assert paper_collect_done(tmp_path, "PMC9")


def test_collect_done_with_recorded_xml_miss(tmp_path: Path):
    ensure_light_bagit(tmp_path)
    write_json_atomic(
        path_json(tmp_path, "PMC8"),
        {"pmcid": "PMC8", "abstract": "A", "_collect_xml": "unavailable"},
    )
    assert paper_collect_done(tmp_path, "PMC8")
