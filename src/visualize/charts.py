from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager


RANKING_METRIC = "interest_share_pct"
TIMESERIES_METRIC = "interest_share_pct"


def configure_japanese_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in ("Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans CJK JP", "IPAexGothic"):
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False


def plot_theme_ranking(ranking: pd.DataFrame, output_path: str | Path) -> None:
    configure_japanese_fonts()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if ranking.empty:
        _plot_empty("Theme Ranking", output)
        return

    metric = RANKING_METRIC if RANKING_METRIC in ranking.columns else "score"
    data = ranking.sort_values(metric, ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(5, len(data) * 0.45)))
    ax.barh(data["topic"], data[metric], color="#2f7d6f")
    ax.set_title("Theme Ranking by Interest Share")
    ax.set_xlabel("Interest share (%)" if metric == "interest_share_pct" else metric)
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    for _, row in data.iterrows():
        label = f" {row[metric]:.1f}%" if metric == "interest_share_pct" else f" {row[metric]:.1f}"
        ax.text(row[metric], row["topic"], label, va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_theme_time_series(time_series: pd.DataFrame, output_path: str | Path, top_topics: list[str]) -> None:
    configure_japanese_fonts()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if time_series.empty or not top_topics:
        _plot_empty("Theme Trend", output)
        return

    data = time_series[time_series["topic"].isin(top_topics)].copy()
    if data.empty:
        _plot_empty("Theme Trend", output)
        return

    metric = TIMESERIES_METRIC if TIMESERIES_METRIC in data.columns else "score"
    pivot = data.pivot_table(index="date", columns="topic", values=metric, aggfunc="sum").fillna(0.0)
    fig, ax = plt.subplots(figsize=(11, 6))
    for topic in pivot.columns:
        ax.plot(pivot.index, pivot[topic], marker="o", linewidth=2, label=topic)
    ax.set_title("Theme Trend by Interest Share")
    ax.set_xlabel("date")
    ax.set_ylabel("Interest share (%)" if metric == "interest_share_pct" else metric)
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _plot_empty(title: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_title(title)
    ax.text(0.5, 0.5, "No data", ha="center", va="center")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
