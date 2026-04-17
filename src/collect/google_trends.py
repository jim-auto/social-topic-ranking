from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.models import TrendRecord


JST = dt.timezone(dt.timedelta(hours=9))


@dataclass(frozen=True)
class GoogleTrendsConfig:
    hl: str = "ja-JP"
    tz: int = 540
    geo: str = "JP"
    pn: str = "japan"
    retries: int = 2
    backoff_factor: float = 0.5
    request_interval_seconds: float = 1.0


class GoogleTrendsCollector:
    """Thin wrapper around pytrends with a stable project-level schema."""

    def __init__(self, config: GoogleTrendsConfig) -> None:
        self.config = config
        self._client: Any | None = None

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "GoogleTrendsCollector":
        trends = settings.get("google_trends", {})
        config = GoogleTrendsConfig(
            hl=trends.get("hl", "ja-JP"),
            tz=int(trends.get("tz", 540)),
            geo=trends.get("geo", "JP"),
            pn=trends.get("pn", "japan"),
            retries=int(trends.get("retries", 2)),
            backoff_factor=float(trends.get("backoff_factor", 0.5)),
            request_interval_seconds=float(trends.get("request_interval_seconds", 1.0)),
        )
        return cls(config)

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                from pytrends.request import TrendReq
            except ImportError as exc:
                raise RuntimeError(
                    "pytrends is not installed. Run `pip install -r requirements.txt`."
                ) from exc
            self._client = TrendReq(
                hl=self.config.hl,
                tz=self.config.tz,
                retries=self.config.retries,
                backoff_factor=self.config.backoff_factor,
            )
        return self._client

    def fetch_trending_searches(self, limit: int = 50) -> list[TrendRecord]:
        """Fetch Japan trending searches.

        Google Trends exposes this endpoint as a ranked list, not absolute volume.
        We convert rank into a 1-100 score so it can be merged with related query
        values while keeping the original rank.
        """

        today = dt.datetime.now(JST).date().isoformat()
        frame = self._with_retry(lambda: self.client.trending_searches(pn=self.config.pn))
        if frame is None or frame.empty:
            return []

        first_column = frame.columns[0]
        keywords = [str(value).strip() for value in frame[first_column].dropna().tolist()]
        records: list[TrendRecord] = []
        capped = keywords[:limit]
        total = max(len(capped), 1)
        for idx, keyword in enumerate(capped, start=1):
            score = round(100.0 * (total - idx + 1) / total, 2)
            records.append(
                TrendRecord(
                    keyword=keyword,
                    score=score,
                    date=today,
                    source="trending_searches",
                    rank=idx,
                )
            )
        return _average_duplicate_interest_records(records)

    def fetch_related_queries(
        self,
        keywords: Iterable[str],
        timeframe: str,
        limit_per_keyword: int = 5,
    ) -> list[TrendRecord]:
        today = dt.datetime.now(JST).date().isoformat()
        records: list[TrendRecord] = []
        for seed in keywords:
            seed = str(seed).strip()
            if not seed:
                continue
            try:
                self._with_retry(
                    lambda seed=seed: self.client.build_payload(
                        [seed],
                        cat=0,
                        timeframe=timeframe,
                        geo=self.config.geo,
                        gprop="",
                    )
                )
                related = self._with_retry(lambda: self.client.related_queries())
            except Exception:
                continue
            self._pause()

            result = related.get(seed) if isinstance(related, dict) else None
            if not result:
                continue

            for relation_type in ("top", "rising"):
                frame = result.get(relation_type)
                if frame is None or frame.empty:
                    continue
                for rank, row in enumerate(frame.head(limit_per_keyword).to_dict("records"), start=1):
                    query = str(row.get("query", "")).strip()
                    if not query:
                        continue
                    score = _coerce_related_score(row.get("value"), relation_type=relation_type)
                    records.append(
                        TrendRecord(
                            keyword=query,
                            score=score,
                            date=today,
                            source=f"related_queries:{relation_type}",
                            rank=rank,
                            related_to=seed,
                        )
                    )
        return records

    def fetch_interest_time_series(
        self,
        keywords: list[str],
        timeframe: str,
        batch_size: int = 5,
    ) -> list[TrendRecord]:
        records: list[TrendRecord] = []
        for batch in _chunks([kw for kw in keywords if str(kw).strip()], min(batch_size, 5)):
            try:
                self._with_retry(
                    lambda batch=batch: self.client.build_payload(
                        batch,
                        cat=0,
                        timeframe=timeframe,
                        geo=self.config.geo,
                        gprop="",
                    )
                )
                frame = self._with_retry(lambda: self.client.interest_over_time())
            except Exception:
                continue
            self._pause()

            if frame is None or frame.empty:
                continue
            frame = frame.reset_index()
            if "isPartial" in frame.columns:
                frame = frame.drop(columns=["isPartial"])

            for row in frame.to_dict("records"):
                raw_date = row.get("date")
                date_text = _format_date(raw_date)
                for keyword in batch:
                    score = row.get(keyword)
                    if score is None:
                        continue
                    records.append(
                        TrendRecord(
                            keyword=keyword,
                            score=float(score),
                            date=date_text,
                            source="interest_over_time",
                        )
                    )
        return records

    def collect(self, settings: dict[str, Any], period: str) -> list[TrendRecord]:
        trends = settings.get("google_trends", {})
        timeframe = trends.get("timeframe", {}).get(period, "now 7-d")
        trending_limit = int(trends.get("trending_limit", 50))
        related_limit = int(trends.get("related_limit", 5))

        records: list[TrendRecord] = []
        seed_keywords = _dedupe_keywords(settings.get("_seed_keywords", []))

        if trends.get("use_trending_searches", True) or not seed_keywords:
            trending_records = self.fetch_trending_searches(limit=trending_limit)
            records.extend(trending_records)
            seed_keywords.extend(record.keyword for record in trending_records)
            seed_keywords = _dedupe_keywords(seed_keywords)

        if trends.get("include_interest_time_series", True) and seed_keywords:
            interest_limit = int(trends.get("interest_keywords_limit", 20))
            batch_size = int(trends.get("interest_batch_size", 5))
            records.extend(
                self.fetch_interest_time_series(
                    seed_keywords[:interest_limit],
                    timeframe=timeframe,
                    batch_size=batch_size,
                )
            )

        if trends.get("include_related_queries", True) and seed_keywords:
            records.extend(
                self.fetch_related_queries(
                    seed_keywords,
                    timeframe=timeframe,
                    limit_per_keyword=related_limit,
                )
            )

        return records

    def _with_retry(self, func: Callable[[], Any]) -> Any:
        last_error: Exception | None = None
        attempts = max(self.config.retries, 0) + 1
        for attempt in range(attempts):
            try:
                return func()
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                time.sleep(self.config.backoff_factor * (2**attempt))
        raise RuntimeError(f"Google Trends request failed: {last_error}") from last_error

    def _pause(self) -> None:
        if self.config.request_interval_seconds > 0:
            time.sleep(self.config.request_interval_seconds)


def records_to_frame(records: list[TrendRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.to_dict() for record in records])


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    size = max(size, 1)
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _dedupe_keywords(keywords: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for keyword in keywords:
        text = str(keyword).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        output.append(text)
        seen.add(key)
    return output


def _average_duplicate_interest_records(records: list[TrendRecord]) -> list[TrendRecord]:
    grouped: dict[tuple[str, str, str], list[float]] = {}
    for record in records:
        key = (record.date, record.keyword, record.source)
        grouped.setdefault(key, []).append(record.score)

    output: list[TrendRecord] = []
    for (date, keyword, source), scores in grouped.items():
        output.append(
            TrendRecord(
                keyword=keyword,
                score=round(sum(scores) / len(scores), 2),
                date=date,
                source=source,
            )
        )
    return output


def _coerce_related_score(value: Any, relation_type: str) -> float:
    if isinstance(value, str) and value.lower() == "breakout":
        return 100.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if relation_type == "rising":
        return min(score, 100.0)
    return score


def _format_date(value: Any) -> str:
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)
