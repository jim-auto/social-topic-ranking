from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TrendRecord:
    """Canonical row used across collection, scoring, and visualization."""

    keyword: str
    score: float
    date: str
    source: str
    rank: int | None = None
    related_to: str | None = None
    related_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "keyword": self.keyword,
            "score": self.score,
            "source": self.source,
            "rank": self.rank,
            "related_to": self.related_to or "",
            "related_terms": "|".join(self.related_terms),
        }


@dataclass(frozen=True)
class TopicDecision:
    topic: str
    confidence: float
    method: str
    matched_keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "confidence": self.confidence,
            "classification_method": self.method,
            "matched_keywords": "|".join(self.matched_keywords),
        }
