from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    if not yaml_path.is_absolute():
        yaml_path = PROJECT_ROOT / yaml_path
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {yaml_path}")
    return data


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return (base or PROJECT_ROOT) / resolved


def ensure_directory(path: str | Path) -> Path:
    directory = resolve_path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
