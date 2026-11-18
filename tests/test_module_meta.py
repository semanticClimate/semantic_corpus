"""Tests for declarative extension-module metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_corpus.module_meta import (
    REGISTERED_MODULES,
    get_facility,
    list_modules,
    load_module,
    module_dir,
)


def test_registered_modules_match_packages():
    root = Path(__file__).resolve().parents[1] / "semantic_corpus"
    for name in REGISTERED_MODULES:
        assert Path(root, name, "module.yaml").is_file()
        assert Path(root, name, "README.md").is_file()
        assert Path(root, name, "__init__.py").is_file()


def test_list_modules_loads_all_three():
    metas = list_modules()
    names = [m["name"] for m in metas]
    assert names == ["corpus", "repositories", "phrases_kg"]
    assert metas[0]["status"] == "primary"
    assert metas[1]["status"] == "extension"
    assert metas[2]["status"] == "extension"


@pytest.mark.parametrize("name", REGISTERED_MODULES)
def test_load_module_validates(name):
    meta = load_module(name)
    assert meta["name"] == name
    assert meta["docs"] == f"docs/modules/{name}/overview.md"
    assert Path(module_dir(name), "module.yaml").is_file()
    docs_path = Path(__file__).resolve().parents[1] / meta["docs"]
    assert docs_path.is_file()
    assert isinstance(meta["facilities"], list)
    assert meta["facilities"], f"{name} should declare at least one facility"


def test_get_facility():
    fac = get_facility("corpus", "bagit")
    assert fac is not None
    assert fac["title"] == "BagIt storage"
    assert get_facility("corpus", "missing") is None


def test_module_package_loaders():
    from semantic_corpus.corpus import MODULE_NAME as c_name
    from semantic_corpus.corpus import load_meta as load_corpus
    from semantic_corpus.phrases_kg import MODULE_NAME as p_name
    from semantic_corpus.phrases_kg import load_meta as load_phrases
    from semantic_corpus.repositories import MODULE_NAME as r_name
    from semantic_corpus.repositories import load_meta as load_repos

    assert c_name == "corpus"
    assert r_name == "repositories"
    assert p_name == "phrases_kg"
    assert load_corpus()["owner"] == "Renu Kumari"
    assert load_repos()["owner"] == "Larisa Beni"
    assert load_phrases()["owner"] == "Neel Kumar"
