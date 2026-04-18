from __future__ import annotations

from typing import Any

import pandas as pd


def build_theme_ranking(frame: pd.DataFrame, top_n: int = 20, latest_only: bool = True) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "rank",
                "topic",
                "score",
                "interest_share_pct",
                "attention_index",
                "keyword_count",
                "avg_keyword_score",
                "top_keywords",
            ]
        )

    df = frame.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
    df["date"] = df["date"].astype(str)
    if latest_only and "date" in df.columns:
        latest_date = max(df["date"])
        df = df[df["date"] == latest_date].copy()

    grouped = (
        df.groupby("topic", dropna=False)
        .agg(
            score=("score", "sum"),
            keyword_count=("keyword", "count"),
            avg_keyword_score=("score", "mean"),
            top_keywords=("keyword", _top_keywords),
        )
        .reset_index()
        .sort_values(["score", "keyword_count", "topic"], ascending=[False, False, True])
    )
    grouped = _add_readable_metrics(grouped).head(top_n).reset_index(drop=True)
    grouped.insert(0, "rank", grouped.index + 1)
    if latest_only and not df.empty:
        grouped["date"] = max(df["date"])
    return _order_ranking_columns(grouped)


def build_theme_time_series(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "topic",
                "score",
                "interest_share_pct",
                "attention_index",
                "keyword_count",
            ]
        )
    df = frame.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
    df["date"] = df["date"].astype(str)
    grouped = (
        df.groupby(["date", "topic"], dropna=False)
        .agg(score=("score", "sum"), keyword_count=("keyword", "count"))
        .reset_index()
    )
    grouped = _add_time_series_metrics(grouped)
    grouped = grouped.sort_values(["date", "score"], ascending=[True, False])
    return _order_time_series_columns(grouped)


def build_audience_breakdown(frame: pd.DataFrame, latest_only: bool = True) -> pd.DataFrame:
    return _build_signal_breakdown(frame, "audience_segment", latest_only=latest_only)


def build_generation_breakdown(frame: pd.DataFrame, latest_only: bool = True) -> pd.DataFrame:
    return _build_signal_breakdown(frame, "generation_segment", latest_only=latest_only)


def add_previous_period_comparison(ranking: pd.DataFrame, time_series: pd.DataFrame) -> pd.DataFrame:
    if ranking.empty or time_series.empty:
        return ranking

    dates = sorted(str(date) for date in time_series["date"].dropna().unique())
    if len(dates) < 2:
        ranking = ranking.copy()
        ranking["previous_score"] = 0.0
        ranking["delta"] = ranking["score"]
        ranking["previous_interest_share_pct"] = 0.0
        ranking["share_delta_pct"] = ranking["interest_share_pct"]
        return _order_ranking_columns(ranking)

    latest_date, previous_date = dates[-1], dates[-2]
    previous_frame = time_series[time_series["date"].astype(str) == previous_date].set_index("topic")
    previous_score = previous_frame["score"].to_dict()
    previous_share = previous_frame["interest_share_pct"].to_dict()
    output = ranking.copy()
    output["previous_date"] = previous_date
    output["previous_score"] = output["topic"].map(lambda topic: float(previous_score.get(topic, 0.0)))
    output["delta"] = output["score"] - output["previous_score"]
    output["delta_rate"] = output.apply(_delta_rate, axis=1)
    output["previous_interest_share_pct"] = output["topic"].map(
        lambda topic: float(previous_share.get(topic, 0.0))
    )
    output["share_delta_pct"] = output["interest_share_pct"] - output["previous_interest_share_pct"]
    output["date"] = latest_date
    return _order_ranking_columns(output)


def _top_keywords(values: pd.Series) -> str:
    return ", ".join(str(value) for value in values.head(5).tolist())


def _delta_rate(row: pd.Series) -> Any:
    previous = float(row.get("previous_score", 0.0))
    if previous == 0:
        return ""
    return round((float(row.get("delta", 0.0)) / previous) * 100, 2)


def _add_readable_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    total_score = float(output["score"].sum())
    max_score = float(output["score"].max()) if not output.empty else 0.0
    output["interest_share_pct"] = output["score"].map(
        lambda score: _safe_percentage(float(score), total_score)
    )
    output["attention_index"] = output["score"].map(
        lambda score: _safe_percentage(float(score), max_score)
    )
    output["avg_keyword_score"] = output["avg_keyword_score"].round(2)
    return output


def _add_time_series_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    totals = output.groupby("date")["score"].transform("sum")
    max_scores = output.groupby("date")["score"].transform("max")
    output["interest_share_pct"] = [
        _safe_percentage(float(score), float(total))
        for score, total in zip(output["score"], totals, strict=False)
    ]
    output["attention_index"] = [
        _safe_percentage(float(score), float(max_score))
        for score, max_score in zip(output["score"], max_scores, strict=False)
    ]
    return output


def _safe_percentage(value: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((value / denominator) * 100, 2)


def _build_signal_breakdown(
    frame: pd.DataFrame,
    segment_column: str,
    latest_only: bool = True,
) -> pd.DataFrame:
    if frame.empty or segment_column not in frame.columns:
        return pd.DataFrame(
            columns=[
                "rank",
                segment_column,
                "interest_share_pct",
                "attention_index",
                "score",
                "keyword_count",
                "top_keywords",
            ]
        )

    df = frame.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
    if latest_only and "date" in df.columns:
        df["date"] = df["date"].astype(str)
        df = df[df["date"] == max(df["date"])].copy()
    grouped = (
        df.groupby(segment_column, dropna=False)
        .agg(
            score=("score", "sum"),
            keyword_count=("keyword", "count"),
            top_keywords=("keyword", _top_keywords),
        )
        .reset_index()
        .sort_values(["score", "keyword_count", segment_column], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    total_score = float(grouped["score"].sum())
    max_score = float(grouped["score"].max()) if not grouped.empty else 0.0
    grouped["interest_share_pct"] = grouped["score"].map(
        lambda score: _safe_percentage(float(score), total_score)
    )
    grouped["attention_index"] = grouped["score"].map(
        lambda score: _safe_percentage(float(score), max_score)
    )
    grouped.insert(0, "rank", grouped.index + 1)
    return _order_columns(
        grouped,
        [
            "rank",
            segment_column,
            "interest_share_pct",
            "attention_index",
            "score",
            "keyword_count",
            "top_keywords",
        ],
    )


def _order_ranking_columns(frame: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "rank",
        "topic",
        "interest_share_pct",
        "attention_index",
        "share_delta_pct",
        "previous_interest_share_pct",
        "score",
        "previous_score",
        "delta",
        "delta_rate",
        "keyword_count",
        "avg_keyword_score",
        "top_keywords",
        "date",
        "previous_date",
    ]
    return _order_columns(frame, preferred)


def _order_time_series_columns(frame: pd.DataFrame) -> pd.DataFrame:
    preferred = ["date", "topic", "interest_share_pct", "attention_index", "score", "keyword_count"]
    return _order_columns(frame, preferred)


def _order_columns(frame: pd.DataFrame, preferred: list[str]) -> pd.DataFrame:
    columns = [column for column in preferred if column in frame.columns]
    columns.extend(column for column in frame.columns if column not in columns)
    return frame[columns]
