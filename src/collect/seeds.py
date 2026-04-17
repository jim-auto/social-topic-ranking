from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import load_yaml, resolve_path


def load_seed_keywords(path: str | Path, limit: int | None = None) -> list[str]:
    config = load_yaml(resolve_path(path))
    return flatten_seed_keywords(config, limit=limit)


def flatten_seed_keywords(config: dict[str, Any], limit: int | None = None) -> list[str]:
    raw = config.get("seed_keywords", config)
    keywords: list[str] = []

    if isinstance(raw, dict):
        for value in raw.values():
            keywords.extend(_coerce_keywords(value))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                keywords.extend(_coerce_keywords(item.get("keywords", [])))
            else:
                keywords.extend(_coerce_keywords(item))

    deduped = _dedupe(keywords)
    if limit is None:
        return deduped
    return deduped[: max(limit, 0)]


def _coerce_keywords(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        output.append(normalized)
        seen.add(key)
    return output
