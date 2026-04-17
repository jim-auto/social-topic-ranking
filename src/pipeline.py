from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from src.collect.google_trends import GoogleTrendsCollector, records_to_frame
from src.collect.seeds import load_seed_keywords
from src.config import PROJECT_ROOT, ensure_directory, load_yaml, resolve_path
from src.preprocess.japanese import JapaneseTextPreprocessor
from src.scoring.scorer import (
    add_previous_period_comparison,
    build_audience_breakdown,
    build_theme_ranking,
    build_theme_time_series,
)
from src.topic.audience import AudienceEstimator
from src.topic.classifier import KeywordTopicClassifier
from src.visualize.charts import plot_theme_ranking, plot_theme_time_series
from src.visualize.site import build_static_site


def run_pipeline(
    settings_path: str | Path = "config/settings.yml",
    themes_path: str | Path = "config/themes.yml",
    audience_path: str | Path | None = None,
    seeds_path: str | Path | None = None,
    input_csv: str | Path | None = None,
    output_dir: str | Path | None = None,
    period: str | None = None,
    limit: int | None = None,
    seed_limit: int | None = None,
) -> dict[str, Path]:
    settings = load_yaml(settings_path)
    themes = load_yaml(themes_path)
    period = period or settings.get("pipeline", {}).get("period", "daily")
    output_directory = ensure_directory(output_dir or settings.get("pipeline", {}).get("output_dir", "outputs"))

    raw = _load_or_collect(settings, input_csv, period, limit, seeds_path, seed_limit)
    preprocessor = JapaneseTextPreprocessor.from_settings(settings)
    preprocessed = preprocessor.transform(raw)

    classifier = KeywordTopicClassifier.from_configs(themes, settings)
    classified = classifier.classify_frame(preprocessed)
    classified = _add_audience_segments(classified, settings, audience_path)

    top_n = int(settings.get("output", {}).get("top_n", 20))
    time_series = build_theme_time_series(classified)
    ranking = build_theme_ranking(classified, top_n=top_n, latest_only=True)
    ranking = add_previous_period_comparison(ranking, time_series)
    audience_breakdown = build_audience_breakdown(classified)

    paths = _write_outputs(settings, output_directory, classified, ranking, time_series, audience_breakdown)
    _write_charts(settings, output_directory, ranking, time_series)
    if settings.get("output", {}).get("build_site", False):
        build_static_site(output_directory, settings.get("output", {}).get("site_dir", "site"))
    return paths


def _add_audience_segments(
    classified: pd.DataFrame,
    settings: dict[str, Any],
    audience_path: str | Path | None,
) -> pd.DataFrame:
    audience_settings = settings.get("audience", {})
    if not audience_settings.get("enabled", True):
        return classified
    configured_path = audience_path or audience_settings.get("config_path", "config/audience.yml")
    audience_config = load_yaml(configured_path)
    estimator = AudienceEstimator.from_config(audience_config)
    return estimator.classify_frame(classified)


def _load_or_collect(
    settings: dict[str, Any],
    input_csv: str | Path | None,
    period: str,
    limit: int | None,
    seeds_path: str | Path | None,
    seed_limit: int | None,
) -> pd.DataFrame:
    configured_input = settings.get("pipeline", {}).get("input_csv") or ""
    source_csv = input_csv or configured_input
    if source_csv:
        return _load_csv(resolve_path(source_csv))

    trends_settings = settings.get("google_trends", {})
    if trends_settings.get("enabled", True):
        try:
            seed_keywords = _load_seed_keywords(settings, seeds_path, seed_limit)
            if seed_keywords:
                settings = dict(settings)
                settings["_seed_keywords"] = seed_keywords
            collector = GoogleTrendsCollector.from_settings(settings)
            records = collector.collect(settings, period=period)
            if limit is not None:
                records = records[:limit]
            frame = records_to_frame(records)
            if not frame.empty:
                _save_raw_snapshot(frame)
                return frame
        except Exception as exc:
            print(f"[warn] Google Trends collection failed: {exc}")

    if settings.get("pipeline", {}).get("sample_when_empty", True):
        return _load_csv(PROJECT_ROOT / "data" / "sample_trends.csv")

    raise RuntimeError("No trend data was collected. Set an input CSV or enable sample_when_empty.")


def _load_seed_keywords(
    settings: dict[str, Any],
    seeds_path: str | Path | None,
    seed_limit: int | None,
) -> list[str]:
    trends_settings = settings.get("google_trends", {})
    if not trends_settings.get("use_seed_keywords", True):
        return []

    configured_path = seeds_path or trends_settings.get("seed_keywords_path")
    if not configured_path:
        return []

    limit = seed_limit if seed_limit is not None else trends_settings.get("seed_keywords_limit")
    limit = int(limit) if limit is not None else None
    return load_seed_keywords(configured_path, limit=limit)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    return pd.read_csv(path)


def _save_raw_snapshot(frame: pd.DataFrame) -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    frame.to_csv(raw_dir / f"google_trends_{timestamp}.csv", index=False, encoding="utf-8-sig")


def _write_outputs(
    settings: dict[str, Any],
    output_dir: Path,
    classified: pd.DataFrame,
    ranking: pd.DataFrame,
    time_series: pd.DataFrame,
    audience_breakdown: pd.DataFrame,
) -> dict[str, Path]:
    output_config = settings.get("output", {})
    paths = {
        "classified_keywords": output_dir / output_config.get("classified_keywords_csv", "classified_keywords.csv"),
        "theme_ranking": output_dir / output_config.get("theme_ranking_csv", "theme_ranking.csv"),
        "theme_timeseries": output_dir / output_config.get("theme_timeseries_csv", "theme_timeseries.csv"),
        "audience_breakdown": output_dir / output_config.get("audience_breakdown_csv", "audience_breakdown.csv"),
        "ranking_chart": output_dir / output_config.get("ranking_chart", "theme_ranking.png"),
        "timeseries_chart": output_dir / output_config.get("timeseries_chart", "theme_timeseries.png"),
    }
    classified.to_csv(paths["classified_keywords"], index=False, encoding="utf-8-sig")
    ranking.to_csv(paths["theme_ranking"], index=False, encoding="utf-8-sig")
    time_series.to_csv(paths["theme_timeseries"], index=False, encoding="utf-8-sig")
    audience_breakdown.to_csv(paths["audience_breakdown"], index=False, encoding="utf-8-sig")
    return paths


def _write_charts(
    settings: dict[str, Any],
    output_dir: Path,
    ranking: pd.DataFrame,
    time_series: pd.DataFrame,
) -> None:
    output_config = settings.get("output", {})
    ranking_chart = output_dir / output_config.get("ranking_chart", "theme_ranking.png")
    timeseries_chart = output_dir / output_config.get("timeseries_chart", "theme_timeseries.png")
    top_topics = ranking["topic"].head(8).tolist() if not ranking.empty else []
    plot_theme_ranking(ranking, ranking_chart)
    plot_theme_time_series(time_series, timeseries_chart, top_topics)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank social topics from Google Trends search behavior.")
    parser.add_argument("--settings", default="config/settings.yml", help="Path to settings YAML.")
    parser.add_argument("--themes", default="config/themes.yml", help="Path to theme YAML.")
    parser.add_argument("--audience", default=None, help="Path to audience signal YAML.")
    parser.add_argument("--seeds", default=None, help="Path to seed keyword YAML.")
    parser.add_argument("--input", default=None, help="Optional CSV input. Skips Google Trends collection.")
    parser.add_argument("--output-dir", default=None, help="Output directory.")
    parser.add_argument("--period", choices=("daily", "weekly"), default=None, help="Trend period.")
    parser.add_argument("--limit", type=int, default=None, help="Limit raw collected records for quick checks.")
    parser.add_argument("--seed-limit", type=int, default=None, help="Limit seed keywords for quick Google Trends checks.")
    parser.add_argument("--build-site", action="store_true", help="Build the static dashboard in site/.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = run_pipeline(
        settings_path=args.settings,
        themes_path=args.themes,
        audience_path=args.audience,
        seeds_path=args.seeds,
        input_csv=args.input,
        output_dir=args.output_dir,
        period=args.period,
        limit=args.limit,
        seed_limit=args.seed_limit,
    )
    if args.build_site:
        build_static_site(args.output_dir or "outputs", "site")
    ranking = pd.read_csv(paths["theme_ranking"])
    print("Outputs:")
    for name, path in paths.items():
        print(f"- {name}: {path}")
    if not ranking.empty:
        columns = [
            column
            for column in ("rank", "topic", "interest_share_pct", "attention_index", "share_delta_pct")
            if column in ranking.columns
        ]
        print("\nTop themes:")
        print(ranking[columns].head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
