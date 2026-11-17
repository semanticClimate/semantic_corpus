"""Load declarative metadata for semantic_corpus extension modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

_PACKAGE_ROOT = Path(__file__).resolve().parent

# First-class extension modules (directory names under this package).
REGISTERED_MODULES = (
    "corpus",
    "repositories",
    "phrases_kg",
)


def module_dir(name: str) -> Path:
    """Return the filesystem directory for a registered module."""
    path = Path(_PACKAGE_ROOT, name)
    if not path.is_dir():
        raise FileNotFoundError(f"Module directory not found: {path}")
    return path


def load_module(name: str) -> Dict[str, Any]:
    """Load and validate ``module.yaml`` for ``name``."""
    if yaml is None:
        raise ImportError("PyYAML is required to load module.yaml (install pyyaml)")
    path = Path(module_dir(name), "module.yaml")
    if not path.is_file():
        raise FileNotFoundError(f"Missing module.yaml for module {name!r}: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"module.yaml must be a mapping: {path}")
    _validate_module_meta(data, expected_name=name, path=path)
    return data


def list_modules() -> List[Dict[str, Any]]:
    """Load metadata for all registered modules (skip missing dirs)."""
    out: List[Dict[str, Any]] = []
    for name in REGISTERED_MODULES:
        path = Path(_PACKAGE_ROOT, name)
        if not path.is_dir():
            continue
        if not Path(path, "module.yaml").is_file():
            continue
        out.append(load_module(name))
    return out


def _validate_module_meta(
    data: Dict[str, Any], *, expected_name: str, path: Path
) -> None:
    required = (
        "name",
        "title",
        "summary",
        "owner",
        "co_authors",
        "status",
        "python_extra",
        "depends_on",
        "docs",
        "facilities",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"{path}: missing fields {missing}")
    if data["name"] != expected_name:
        raise ValueError(
            f"{path}: name {data['name']!r} does not match directory {expected_name!r}"
        )
    status = data["status"]
    if status not in {"primary", "extension", "bridge"}:
        raise ValueError(f"{path}: invalid status {status!r}")
    if not isinstance(data["facilities"], list):
        raise ValueError(f"{path}: facilities must be a list")
    for facility in data["facilities"]:
        if not isinstance(facility, dict):
            raise ValueError(f"{path}: each facility must be a mapping")
        for key in ("id", "title", "summary"):
            if key not in facility:
                raise ValueError(f"{path}: facility missing {key!r}")


def get_facility(module_name: str, facility_id: str) -> Optional[Dict[str, Any]]:
    """Return one facility dict or None."""
    meta = load_module(module_name)
    for facility in meta.get("facilities") or []:
        if facility.get("id") == facility_id:
            return facility
    return None
