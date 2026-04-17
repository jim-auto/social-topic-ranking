from __future__ import annotations

import csv
import datetime as dt
import html
import shutil
from pathlib import Path
from typing import Any


SITE_CSS = """\
:root {
  color-scheme: light;
  --bg: #f7f5f0;
  --panel: #ffffff;
  --ink: #1b1d1f;
  --muted: #6b7178;
  --line: #d9d4ca;
  --accent: #1f7a68;
  --accent-2: #b24c2f;
  --soft: #e9f2ef;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Yu Gothic", "Meiryo", "Noto Sans JP", system-ui, sans-serif;
  font-size: 16px;
  letter-spacing: 0;
}

a {
  color: inherit;
}

.page {
  min-height: 100vh;
}

.hero {
  background: #f0ede5;
  border-bottom: 1px solid var(--line);
}

.hero-inner,
.section {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
}

.hero-inner {
  min-height: 310px;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 32px;
  align-items: center;
  padding: 42px 0 28px;
}

.title-block h1 {
  margin: 0 0 14px;
  font-size: clamp(2rem, 4vw, 4.1rem);
  line-height: 1.02;
  font-weight: 800;
}

.title-block p {
  max-width: 700px;
  margin: 0;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.8;
}

.hero-chart {
  width: 100%;
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 10px;
}

.hero-chart img,
.chart-panel img {
  display: block;
  width: 100%;
  height: auto;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 26px;
}

.metric {
  border-top: 3px solid var(--accent);
  background: rgba(255, 255, 255, 0.68);
  padding: 14px 12px;
}

.metric-label {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
}

.metric-value {
  display: block;
  margin-top: 6px;
  font-size: 1.45rem;
  font-weight: 750;
  line-height: 1.2;
}

.section {
  padding: 30px 0 44px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
  margin-bottom: 14px;
}

.section-header h2 {
  margin: 0;
  font-size: 1.6rem;
}

.section-header span {
  color: var(--muted);
  font-size: 0.92rem;
}

.ranking-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
  border: 1px solid var(--line);
}

.ranking-table th,
.ranking-table td {
  padding: 13px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

.ranking-table th {
  color: var(--muted);
  font-weight: 700;
  font-size: 0.84rem;
  background: #fbfaf7;
}

.ranking-table td.num,
.ranking-table th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.rank {
  width: 44px;
  font-weight: 800;
  color: var(--accent-2);
}

.topic {
  min-width: 150px;
  font-weight: 800;
}

.bar-cell {
  min-width: 170px;
}

.share-bar {
  height: 10px;
  border-radius: 999px;
  background: #e5e1d8;
  overflow: hidden;
  margin-top: 6px;
}

.share-bar span {
  display: block;
  height: 100%;
  background: var(--accent);
}

.keywords {
  max-width: 440px;
  color: var(--muted);
  line-height: 1.55;
}

.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.chart-panel {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 10px;
}

.downloads {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.download-link {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 10px 12px;
  text-decoration: none;
  font-weight: 700;
}

.download-link:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.footer {
  border-top: 1px solid var(--line);
  padding: 18px 0 32px;
  color: var(--muted);
}

@media (max-width: 860px) {
  .hero-inner {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .metrics,
  .charts {
    grid-template-columns: 1fr;
  }

  .ranking-table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }

  .keywords {
    min-width: 280px;
    white-space: normal;
  }
}
"""


def build_static_site(
    outputs_dir: str | Path = "outputs",
    site_dir: str | Path = "site",
) -> Path:
    outputs = Path(outputs_dir)
    site = Path(site_dir)
    assets = site / "assets"
    data_dir = site / "data"
    assets.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    ranking_path = outputs / "theme_ranking.csv"
    time_series_path = outputs / "theme_timeseries.csv"
    classified_path = outputs / "classified_keywords.csv"
    audience_path = outputs / "audience_breakdown.csv"
    if not ranking_path.exists():
        raise FileNotFoundError(f"Missing ranking output: {ranking_path}")

    ranking = _read_csv(ranking_path)
    time_series = _read_csv(time_series_path) if time_series_path.exists() else []
    audience = _read_csv(audience_path) if audience_path.exists() else []
    latest_date = ranking[0].get("date", "") if ranking else ""

    _copy_if_exists(outputs / "theme_ranking.png", assets / "theme_ranking.png")
    _copy_if_exists(outputs / "theme_timeseries.png", assets / "theme_timeseries.png")
    _copy_if_exists(ranking_path, data_dir / "theme_ranking.csv")
    _copy_if_exists(time_series_path, data_dir / "theme_timeseries.csv")
    _copy_if_exists(classified_path, data_dir / "classified_keywords.csv")
    _copy_if_exists(audience_path, data_dir / "audience_breakdown.csv")

    (site / "styles.css").write_text(SITE_CSS, encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    (site / "index.html").write_text(
        _render_html(
            ranking=ranking,
            time_series=time_series,
            audience=audience,
            latest_date=latest_date,
        ),
        encoding="utf-8",
    )
    return site / "index.html"


def _render_html(
    ranking: list[dict[str, str]],
    time_series: list[dict[str, str]],
    audience: list[dict[str, str]],
    latest_date: str,
) -> str:
    top = ranking[0] if ranking else {}
    total_keywords = sum(_to_int(row.get("keyword_count")) for row in ranking)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    theme_count = len(ranking)

    rows = "\n".join(_render_ranking_row(row) for row in ranking)
    audience_rows = "\n".join(_render_audience_row(row) for row in audience)
    max_share = max((_to_float(row.get("interest_share_pct")) for row in ranking), default=0.0)
    subtitle = (
        f"{html.escape(latest_date)} / {theme_count} themes / {total_keywords} keywords"
        if latest_date
        else f"{theme_count} themes / {total_keywords} keywords"
    )

    return f"""\
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Social Topic Ranking</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="page">
    <header class="hero">
      <div class="hero-inner">
        <div class="title-block">
          <h1>Social Topic Ranking</h1>
          <p>検索行動からテーマ単位の関心シェアを集計したダッシュボード。</p>
          <div class="metrics" aria-label="summary">
            {_metric("Top Theme", top.get("topic", "-"))}
            {_metric("Interest Share", _fmt_pct(top.get("interest_share_pct")))}
            {_metric("Attention Index", _fmt_number(top.get("attention_index")))}
            {_metric("Data", latest_date or "-")}
          </div>
        </div>
        <div class="hero-chart">
          <img src="assets/theme_ranking.png" alt="Theme ranking chart">
        </div>
      </div>
    </header>

    <section class="section">
      <div class="section-header">
        <h2>Ranking</h2>
        <span>{subtitle}</span>
      </div>
      <table class="ranking-table">
        <thead>
          <tr>
            <th class="rank">#</th>
            <th>Theme</th>
            <th class="num">Interest Share</th>
            <th class="num">Index</th>
            <th class="num">Keywords</th>
            <th>Top Keywords</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <div class="section-header">
        <h2>Charts</h2>
        <span>Generated {html.escape(generated_at)}</span>
      </div>
      <div class="charts">
        <div class="chart-panel">
          <img src="assets/theme_ranking.png" alt="Interest share by theme">
        </div>
        <div class="chart-panel">
          <img src="assets/theme_timeseries.png" alt="Interest share time series">
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <h2>Audience Signals</h2>
        <span>query-level estimate, not user identity</span>
      </div>
      <table class="ranking-table">
        <thead>
          <tr>
            <th class="rank">#</th>
            <th>Segment</th>
            <th class="num">Interest Share</th>
            <th class="num">Index</th>
            <th class="num">Keywords</th>
            <th>Top Keywords</th>
          </tr>
        </thead>
        <tbody>
          {audience_rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <div class="section-header">
        <h2>Data</h2>
        <span>{len(time_series)} trend rows</span>
      </div>
      <div class="downloads">
        <a class="download-link" href="data/theme_ranking.csv">theme_ranking.csv</a>
        <a class="download-link" href="data/theme_timeseries.csv">theme_timeseries.csv</a>
        <a class="download-link" href="data/audience_breakdown.csv">audience_breakdown.csv</a>
        <a class="download-link" href="data/classified_keywords.csv">classified_keywords.csv</a>
      </div>
    </section>
  </main>
  <footer class="footer">
    <div class="section">source: Google Trends via pytrends / generated by social-topic-ranking</div>
  </footer>
</body>
</html>
<!-- max_share={max_share:.2f} -->
"""


def _render_ranking_row(row: dict[str, str]) -> str:
    share = _to_float(row.get("interest_share_pct"))
    index = _to_float(row.get("attention_index"))
    keywords = html.escape(row.get("top_keywords", ""))
    width = max(0.0, min(100.0, share))
    return f"""\
          <tr>
            <td class="rank">{html.escape(row.get("rank", ""))}</td>
            <td class="topic">{html.escape(row.get("topic", ""))}</td>
            <td class="num bar-cell">{share:.2f}%<div class="share-bar"><span style="width: {width:.2f}%"></span></div></td>
            <td class="num">{index:.2f}</td>
            <td class="num">{html.escape(row.get("keyword_count", ""))}</td>
            <td class="keywords">{keywords}</td>
          </tr>"""


def _render_audience_row(row: dict[str, str]) -> str:
    share = _to_float(row.get("interest_share_pct"))
    index = _to_float(row.get("attention_index"))
    keywords = html.escape(row.get("top_keywords", ""))
    width = max(0.0, min(100.0, share))
    return f"""\
          <tr>
            <td class="rank">{html.escape(row.get("rank", ""))}</td>
            <td class="topic">{html.escape(row.get("audience_segment", ""))}</td>
            <td class="num bar-cell">{share:.2f}%<div class="share-bar"><span style="width: {width:.2f}%"></span></div></td>
            <td class="num">{index:.2f}</td>
            <td class="num">{html.escape(row.get("keyword_count", ""))}</td>
            <td class="keywords">{keywords}</td>
          </tr>"""


def _metric(label: str, value: str) -> str:
    return f"""\
            <div class="metric">
              <span class="metric-label">{html.escape(label)}</span>
              <span class="metric-value">{html.escape(value)}</span>
            </div>"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copy2(source, destination)


def _fmt_pct(value: Any) -> str:
    number = _to_float(value)
    return f"{number:.2f}%"


def _fmt_number(value: Any) -> str:
    return f"{_to_float(value):.2f}"


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
