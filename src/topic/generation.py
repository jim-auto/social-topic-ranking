from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.preprocess.japanese import JapaneseTextPreprocessor


@dataclass(frozen=True)
class GenerationSegment:
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class GenerationDecision:
    segment: str
    confidence: float
    method: str
    matched_keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_segment": self.segment,
            "generation_confidence": self.confidence,
            "generation_method": self.method,
            "generation_matched_keywords": "|".join(self.matched_keywords),
        }


class GenerationEstimator:
    """Estimate generation/life-stage signals from query text.

    This labels search terms, not people. A query such as "小学生 行方不明"
    contains a student/child context, but it does not mean the searcher is a
    student. Keep this as an aggregate weak signal.
    """

    def __init__(self, segments: list[GenerationSegment], default_segment: str) -> None:
        self.segments = segments
        self.default_segment = default_segment
        self.preprocessor = JapaneseTextPreprocessor()
        self.keyword_index = self._build_keyword_index(segments)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "GenerationEstimator":
        default_segment = str(config.get("default_segment", "世代不明"))
        segments = [
            GenerationSegment(
                name=str(item.get("name", "")).strip(),
                keywords=tuple(str(keyword) for keyword in item.get("keywords", [])),
            )
            for item in config.get("segments", [])
        ]
        if not segments:
            raise ValueError("No generation segments found in config/generation.yml")
        return cls(segments=segments, default_segment=default_segment)

    def classify_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        output: list[dict[str, Any]] = []
        for row in frame.to_dict("records"):
            decision = self.classify_keyword(
                keyword=str(row.get("keyword", "")),
                normalized_keyword=str(row.get("normalized_keyword", "")),
                nouns=str(row.get("nouns", "")).split("|"),
                related_to=_clean_optional_text(row.get("related_to", "")),
            )
            merged = dict(row)
            merged.update(decision.to_dict())
            output.append(merged)
        return pd.DataFrame(output)

    def classify_keyword(
        self,
        keyword: str,
        normalized_keyword: str = "",
        nouns: list[str] | None = None,
        related_to: str = "",
    ) -> GenerationDecision:
        text = normalized_keyword or self.preprocessor.normalize_text(keyword)
        compact_text = _compact(text)
        context_text = self.preprocessor.normalize_text(related_to) if related_to else ""
        compact_context_text = _compact(context_text)
        token_set = {self.preprocessor.normalize_text(token) for token in (nouns or []) if token}
        compact_token_set = {_compact(token) for token in token_set}

        best_segment = self.default_segment
        best_score = 0.0
        best_matches: list[str] = []

        for segment in self.segments:
            score = 0.0
            matches: list[str] = []
            score += _explicit_generation_bonus(segment.name, compact_text, compact_context_text)
            for keyword_pattern in self.keyword_index.get(segment.name, ()):
                compact_pattern = _compact(keyword_pattern)
                if keyword_pattern in token_set or compact_pattern in compact_token_set:
                    score += 2.0
                    matches.append(keyword_pattern)
                elif keyword_pattern in text or compact_pattern in compact_text:
                    score += 1.0
                    matches.append(keyword_pattern)
                elif context_text and (
                    keyword_pattern in context_text or compact_pattern in compact_context_text
                ):
                    score += 0.75
                    matches.append(keyword_pattern)
            if score > best_score:
                best_segment = segment.name
                best_score = score
                best_matches = matches
            elif score == best_score and score > 0:
                best_segment = self.default_segment
                best_matches = []

        if best_score <= 0 or best_segment == self.default_segment:
            return GenerationDecision(self.default_segment, 0.25, "keyword_signal")
        confidence = min(0.95, 0.45 + best_score * 0.15)
        return GenerationDecision(
            segment=best_segment,
            confidence=confidence,
            method="keyword_signal",
            matched_keywords=tuple(best_matches),
        )

    def _build_keyword_index(self, segments: list[GenerationSegment]) -> dict[str, tuple[str, ...]]:
        index: dict[str, tuple[str, ...]] = {}
        for segment in segments:
            normalized = [self.preprocessor.normalize_text(keyword) for keyword in segment.keywords]
            index[segment.name] = tuple(keyword for keyword in normalized if keyword)
        return index


def _explicit_generation_bonus(segment_name: str, compact_text: str, compact_context_text: str) -> float:
    haystack = compact_text + " " + compact_context_text
    if segment_name == "10代・学生":
        return _marker_bonus(haystack, ("10代", "中学生", "高校生", "小学生"))
    if segment_name == "20代":
        return _marker_bonus(haystack, ("20代", "大学生", "就活", "新卒"))
    if segment_name == "30代":
        return _marker_bonus(haystack, ("30代", "妊娠", "出産", "保育園"))
    if segment_name == "40代":
        return _marker_bonus(haystack, ("40代", "授業参観", "中学受験", "更年期"))
    if segment_name == "50代以上":
        return _marker_bonus(haystack, ("50代", "60代", "70代", "年金", "老後", "定年"))
    return 0.0


def _marker_bonus(text: str, markers: tuple[str, ...]) -> float:
    for marker in markers:
        if marker in text:
            return 3.0
    return 0.0


def _compact(text: str) -> str:
    return "".join(str(text).split())


def _clean_optional_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()
