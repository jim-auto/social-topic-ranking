from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.models import TopicDecision
from src.preprocess.japanese import JapaneseTextPreprocessor


@dataclass(frozen=True)
class TopicDefinition:
    name: str
    description: str
    keywords: tuple[str, ...]


class KeywordTopicClassifier:
    def __init__(
        self,
        topics: list[TopicDefinition],
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.topics = topics
        self.settings = settings or {}
        self.preprocessor = JapaneseTextPreprocessor()
        self.fallback_topic = "その他"
        if topics:
            self.fallback_topic = next((topic.name for topic in topics if topic.name == "その他"), topics[-1].name)
        self.keyword_index = self._build_keyword_index(topics)
        self.llm = self._build_llm_classifier()

    @classmethod
    def from_configs(
        cls,
        themes_config: dict[str, Any],
        settings: dict[str, Any],
    ) -> "KeywordTopicClassifier":
        topics = []
        for item in themes_config.get("topics", []):
            topics.append(
                TopicDefinition(
                    name=str(item.get("name", "")).strip(),
                    description=str(item.get("description", "")).strip(),
                    keywords=tuple(str(keyword) for keyword in item.get("keywords", [])),
                )
            )
        if not topics:
            raise ValueError("No topics found in config/themes.yml")
        return cls(topics=topics, settings=settings)

    def classify_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy()
        rows = df.to_dict("records")
        decisions = self._classify_with_llm(rows)

        output: list[dict[str, Any]] = []
        min_confidence = float(
            self.settings.get("classification", {})
            .get("llm", {})
            .get("min_confidence", 0.65)
        )
        for row in rows:
            keyword = str(row.get("keyword", ""))
            decision = decisions.get(keyword)
            if decision is None or decision.confidence < min_confidence:
                decision = self.classify_keyword(
                    keyword=keyword,
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
        normalized_keyword: str | None = None,
        nouns: list[str] | None = None,
        related_to: str = "",
    ) -> TopicDecision:
        text = normalized_keyword or self.preprocessor.normalize_text(keyword)
        compact_text = _compact(text)
        context_text = self.preprocessor.normalize_text(related_to) if related_to else ""
        compact_context_text = _compact(context_text)
        token_set = {self.preprocessor.normalize_text(token) for token in (nouns or []) if token}
        compact_token_set = {_compact(token) for token in token_set}
        best_topic = self.fallback_topic
        best_score = 0.0
        best_matches: list[str] = []

        for topic in self.topics:
            if topic.name == self.fallback_topic:
                continue
            score = 0.0
            matches: list[str] = []
            for keyword_pattern in self.keyword_index.get(topic.name, ()):
                if not keyword_pattern:
                    continue
                compact_pattern = _compact(keyword_pattern)
                if keyword_pattern in token_set:
                    score += 2.0
                    matches.append(keyword_pattern)
                elif compact_pattern in compact_token_set:
                    score += 2.0
                    matches.append(keyword_pattern)
                elif keyword_pattern in text:
                    score += 1.0
                    matches.append(keyword_pattern)
                elif compact_pattern in compact_text:
                    score += 1.0
                    matches.append(keyword_pattern)
                elif context_text and keyword_pattern in context_text:
                    score += 0.75
                    matches.append(keyword_pattern)
                elif compact_context_text and compact_pattern in compact_context_text:
                    score += 0.75
                    matches.append(keyword_pattern)
            if score > best_score:
                best_topic = topic.name
                best_score = score
                best_matches = matches

        if best_score <= 0:
            return TopicDecision(topic=self.fallback_topic, confidence=0.25, method="keyword_fallback")
        confidence = min(0.95, 0.5 + best_score * 0.15)
        return TopicDecision(
            topic=best_topic,
            confidence=confidence,
            method="keyword_fallback",
            matched_keywords=tuple(best_matches),
        )

    def _classify_with_llm(self, rows: list[dict[str, Any]]) -> dict[str, TopicDecision]:
        if self.llm is None:
            return {}
        try:
            return self.llm.classify_many(rows)
        except Exception:
            return {}

    def _build_keyword_index(self, topics: list[TopicDefinition]) -> dict[str, tuple[str, ...]]:
        index: dict[str, tuple[str, ...]] = {}
        for topic in topics:
            normalized = [self.preprocessor.normalize_text(keyword) for keyword in topic.keywords]
            index[topic.name] = tuple(keyword for keyword in normalized if keyword)
        return index

    def _build_llm_classifier(self) -> "OpenAITopicClassifier | None":
        llm_config = self.settings.get("classification", {}).get("llm", {})
        if not llm_config.get("enabled", False):
            return None
        provider = llm_config.get("provider", "openai")
        if provider != "openai":
            return None
        return OpenAITopicClassifier(self.topics, llm_config)


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


class OpenAITopicClassifier:
    def __init__(self, topics: list[TopicDefinition], config: dict[str, Any]) -> None:
        self.topics = topics
        self.model = config.get("model") or os.getenv("OPENAI_TOPIC_MODEL", "gpt-4o-mini")
        self.client = self._build_client()

    def classify_many(self, rows: list[dict[str, Any]]) -> dict[str, TopicDecision]:
        if self.client is None:
            return {}
        keywords = [str(row.get("keyword", "")) for row in rows if row.get("keyword")]
        if not keywords:
            return {}

        prompt = self._build_prompt(keywords)
        response = self.client.responses.create(model=self.model, input=prompt)
        text = getattr(response, "output_text", "")
        payload = json.loads(text)
        decisions: dict[str, TopicDecision] = {}
        valid_topics = {topic.name for topic in self.topics}
        for item in payload:
            keyword = str(item.get("keyword", ""))
            topic = str(item.get("topic", ""))
            if not keyword or topic not in valid_topics:
                continue
            confidence = float(item.get("confidence", 0.0))
            decisions[keyword] = TopicDecision(topic=topic, confidence=confidence, method="llm")
        return decisions

    def _build_client(self) -> Any | None:
        if not os.getenv("OPENAI_API_KEY"):
            return None
        try:
            from openai import OpenAI
        except ImportError:
            return None
        return OpenAI()

    def _build_prompt(self, keywords: list[str]) -> str:
        topics_text = "\n".join(
            f"- {topic.name}: {topic.description}" for topic in self.topics
        )
        keywords_text = "\n".join(f"- {keyword}" for keyword in keywords)
        return (
            "日本語検索ワードを、指定テーマのいずれか1つに分類してください。\n"
            "出力はJSON配列のみ。各要素は keyword, topic, confidence を持たせてください。\n"
            "confidence は0から1の数値です。\n\n"
            f"テーマ:\n{topics_text}\n\n"
            f"検索ワード:\n{keywords_text}"
        )
