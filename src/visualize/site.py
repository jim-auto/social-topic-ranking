from __future__ import annotations

import csv
import datetime as dt
import html
import json
import shutil
from pathlib import Path
from typing import Any


ALL_FILTER_VALUE = "__all__"
AUDIENCE_FILTER_ORDER = ["男性寄り", "女性寄り", "中立・不明"]
GENERATION_FILTER_ORDER = ["10代・学生", "20代", "30代", "40代", "50代以上", "世代不明"]

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

.filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 240px)) auto;
  gap: 12px;
  align-items: end;
  margin: 0 0 14px;
}

.filter-control {
  display: grid;
  gap: 6px;
}

.filter-control span {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.filter-control select,
.filter-reset {
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
}

.filter-control select {
  width: 100%;
  padding: 0 34px 0 12px;
}

.filter-reset {
  padding: 0 14px;
  font-weight: 750;
  cursor: pointer;
}

.filter-reset:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.filter-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 16px;
}

.filter-summary-item {
  border-left: 3px solid var(--accent);
  background: rgba(255, 255, 255, 0.7);
  padding: 12px;
  min-width: 0;
}

.filter-summary-label {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
}

.filter-summary-value {
  display: block;
  margin-top: 5px;
  font-size: 1.18rem;
  font-weight: 800;
  line-height: 1.25;
  overflow-wrap: anywhere;
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

.empty-row {
  color: var(--muted);
  text-align: center;
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
  .charts,
  .filter-summary {
    grid-template-columns: 1fr;
  }

  .filters {
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


SITE_JS = """\
(() => {
  const ALL = "__all__";
  const state = {
    records: [],
  };

  const audienceFilter = document.querySelector("#audience-filter");
  const generationFilter = document.querySelector("#generation-filter");
  const resetButton = document.querySelector("#filter-reset");
  const rankingBody = document.querySelector("#ranking-body");
  const rankingSubtitle = document.querySelector("#ranking-subtitle");
  const topTheme = document.querySelector("#filter-top-theme");
  const topShare = document.querySelector("#filter-top-share");
  const topIndex = document.querySelector("#filter-top-index");
  const keywordCount = document.querySelector("#filter-keyword-count");

  if (!audienceFilter || !generationFilter || !rankingBody) {
    return;
  }

  const formatNumber = new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
  const formatInteger = new Intl.NumberFormat("ja-JP");

  audienceFilter.addEventListener("change", render);
  generationFilter.addEventListener("change", render);
  if (resetButton) {
    resetButton.addEventListener("click", () => {
      audienceFilter.value = ALL;
      generationFilter.value = ALL;
      render();
    });
  }

  fetch("data/filter_records.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`filter data ${response.status}`);
      }
      return response.json();
    })
    .then((records) => {
      state.records = Array.isArray(records) ? records : [];
      render();
    })
    .catch(() => {
      setSummary("-", "0.00%", "0.00", "0");
    });

  function render() {
    if (!state.records.length) {
      return;
    }

    const filtered = state.records.filter((record) => {
      const audienceMatch =
        audienceFilter.value === ALL || record.audience_segment === audienceFilter.value;
      const generationMatch =
        generationFilter.value === ALL || record.generation_segment === generationFilter.value;
      return audienceMatch && generationMatch;
    });

    const ranking = buildRanking(filtered);
    rankingBody.innerHTML = ranking.length
      ? ranking.map(renderRow).join("")
      : '<tr><td class="empty-row" colspan="6">該当データなし</td></tr>';

    const uniqueDates = [...new Set(filtered.map((record) => record.date).filter(Boolean))];
    if (rankingSubtitle) {
      const prefix = uniqueDates.length ? `${uniqueDates[0]} / ` : "";
      rankingSubtitle.textContent = `${prefix}${ranking.length} themes / ${filtered.length} keywords`;
    }

    if (ranking.length) {
      const lead = ranking[0];
      setSummary(
        lead.topic,
        `${formatNumber.format(lead.interestShare)}%`,
        formatNumber.format(lead.attentionIndex),
        formatInteger.format(filtered.length),
      );
    } else {
      setSummary("-", "0.00%", "0.00", "0");
    }
  }

  function buildRanking(records) {
    const grouped = new Map();
    records.forEach((record) => {
      const topic = record.topic || "その他";
      const score = Number(record.score) || 0;
      if (!grouped.has(topic)) {
        grouped.set(topic, {
          topic,
          score: 0,
          keywordCount: 0,
          keywords: [],
        });
      }
      const entry = grouped.get(topic);
      entry.score += score;
      entry.keywordCount += 1;
      entry.keywords.push({
        keyword: record.keyword || "",
        score,
      });
    });

    const entries = [...grouped.values()].sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      if (right.keywordCount !== left.keywordCount) {
        return right.keywordCount - left.keywordCount;
      }
      return left.topic.localeCompare(right.topic, "ja");
    });
    const totalScore = entries.reduce((sum, entry) => sum + entry.score, 0);
    const maxScore = entries.length ? entries[0].score : 0;

    return entries.slice(0, 20).map((entry, index) => ({
      rank: index + 1,
      topic: entry.topic,
      interestShare: totalScore > 0 ? (entry.score / totalScore) * 100 : 0,
      attentionIndex: maxScore > 0 ? (entry.score / maxScore) * 100 : 0,
      keywordCount: entry.keywordCount,
      topKeywords: entry.keywords
        .sort((left, right) => right.score - left.score)
        .slice(0, 5)
        .map((item) => item.keyword)
        .filter(Boolean)
        .join(", "),
    }));
  }

  function renderRow(row) {
    const width = Math.max(0, Math.min(100, row.interestShare));
    return `
          <tr>
            <td class="rank">${escapeHtml(String(row.rank))}</td>
            <td class="topic">${escapeHtml(row.topic)}</td>
            <td class="num bar-cell">${formatNumber.format(row.interestShare)}%<div class="share-bar"><span style="width: ${formatNumber.format(width)}%"></span></div></td>
            <td class="num">${formatNumber.format(row.attentionIndex)}</td>
            <td class="num">${formatInteger.format(row.keywordCount)}</td>
            <td class="keywords">${escapeHtml(row.topKeywords)}</td>
          </tr>`;
  }

  function setSummary(theme, share, index, keywords) {
    if (topTheme) {
      topTheme.textContent = theme;
    }
    if (topShare) {
      topShare.textContent = share;
    }
    if (topIndex) {
      topIndex.textContent = index;
    }
    if (keywordCount) {
      keywordCount.textContent = keywords;
    }
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (char) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[char];
    });
  }
})();
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
    generation_path = outputs / "generation_breakdown.csv"
    if not ranking_path.exists():
        raise FileNotFoundError(f"Missing ranking output: {ranking_path}")

    ranking = _read_csv(ranking_path)
    time_series = _read_csv(time_series_path) if time_series_path.exists() else []
    classified = _read_csv(classified_path) if classified_path.exists() else []
    audience = _read_csv(audience_path) if audience_path.exists() else []
    generation = _read_csv(generation_path) if generation_path.exists() else []
    latest_date = ranking[0].get("date", "") if ranking else ""

    _copy_if_exists(outputs / "theme_ranking.png", assets / "theme_ranking.png")
    _copy_if_exists(outputs / "theme_timeseries.png", assets / "theme_timeseries.png")
    _copy_if_exists(ranking_path, data_dir / "theme_ranking.csv")
    _copy_if_exists(time_series_path, data_dir / "theme_timeseries.csv")
    _copy_if_exists(classified_path, data_dir / "classified_keywords.csv")
    _copy_if_exists(audience_path, data_dir / "audience_breakdown.csv")
    _copy_if_exists(generation_path, data_dir / "generation_breakdown.csv")

    (data_dir / "filter_records.json").write_text(
        json.dumps(_filter_records(classified, latest_date), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (site / "styles.css").write_text(SITE_CSS, encoding="utf-8")
    (site / "app.js").write_text(SITE_JS, encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    (site / "index.html").write_text(
        _render_html(
            ranking=ranking,
            time_series=time_series,
            audience=audience,
            generation=generation,
            latest_date=latest_date,
        ),
        encoding="utf-8",
    )
    return site / "index.html"


def _render_html(
    ranking: list[dict[str, str]],
    time_series: list[dict[str, str]],
    audience: list[dict[str, str]],
    generation: list[dict[str, str]],
    latest_date: str,
) -> str:
    top = ranking[0] if ranking else {}
    total_keywords = sum(_to_int(row.get("keyword_count")) for row in ranking)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    theme_count = len(ranking)

    rows = "\n".join(_render_ranking_row(row) for row in ranking)
    audience_rows = "\n".join(_render_audience_row(row) for row in audience)
    generation_rows = "\n".join(_render_generation_row(row) for row in generation)
    max_share = max((_to_float(row.get("interest_share_pct")) for row in ranking), default=0.0)
    audience_options = _render_select_options(
        _segment_options(audience, "audience_segment", AUDIENCE_FILTER_ORDER)
    )
    generation_options = _render_select_options(
        _segment_options(generation, "generation_segment", GENERATION_FILTER_ORDER)
    )
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
  <script src="app.js" defer></script>
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
        <span id="ranking-subtitle">{subtitle}</span>
      </div>
      <div class="filters" aria-label="ranking filters">
        <label class="filter-control" for="audience-filter">
          <span>男女寄り</span>
          <select id="audience-filter">
            {audience_options}
          </select>
        </label>
        <label class="filter-control" for="generation-filter">
          <span>世代</span>
          <select id="generation-filter">
            {generation_options}
          </select>
        </label>
        <button class="filter-reset" id="filter-reset" type="button">Reset</button>
      </div>
      <div class="filter-summary" aria-label="filtered summary">
        {_filter_summary_item("Top Theme", "filter-top-theme", top.get("topic", "-"))}
        {_filter_summary_item("Interest Share", "filter-top-share", _fmt_pct(top.get("interest_share_pct")))}
        {_filter_summary_item("Attention Index", "filter-top-index", _fmt_number(top.get("attention_index")))}
        {_filter_summary_item("Keywords", "filter-keyword-count", str(total_keywords))}
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
        <tbody id="ranking-body">
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
        <h2>Generation Signals</h2>
        <span>life-stage signal in query text, not user age</span>
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
          {generation_rows}
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
        <a class="download-link" href="data/generation_breakdown.csv">generation_breakdown.csv</a>
        <a class="download-link" href="data/classified_keywords.csv">classified_keywords.csv</a>
        <a class="download-link" href="data/filter_records.json">filter_records.json</a>
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


def _render_generation_row(row: dict[str, str]) -> str:
    share = _to_float(row.get("interest_share_pct"))
    index = _to_float(row.get("attention_index"))
    keywords = html.escape(row.get("top_keywords", ""))
    width = max(0.0, min(100.0, share))
    return f"""\
          <tr>
            <td class="rank">{html.escape(row.get("rank", ""))}</td>
            <td class="topic">{html.escape(row.get("generation_segment", ""))}</td>
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


def _filter_summary_item(label: str, element_id: str, value: str) -> str:
    return f"""\
        <div class="filter-summary-item">
          <span class="filter-summary-label">{html.escape(label)}</span>
          <span class="filter-summary-value" id="{html.escape(element_id)}">{html.escape(value)}</span>
        </div>"""


def _render_select_options(options: list[str]) -> str:
    rendered = [f'<option value="{ALL_FILTER_VALUE}">すべて</option>']
    rendered.extend(
        f'<option value="{html.escape(option)}">{html.escape(option)}</option>' for option in options
    )
    return "\n            ".join(rendered)


def _segment_options(rows: list[dict[str, str]], field: str, preferred: list[str]) -> list[str]:
    seen = {row.get(field, "") for row in rows if row.get(field)}
    options = list(preferred)
    options.extend(sorted(value for value in seen if value not in preferred))
    return options


def _filter_records(rows: list[dict[str, str]], latest_date: str) -> list[dict[str, Any]]:
    source_rows = rows
    if latest_date:
        source_rows = [row for row in rows if row.get("date", "") == latest_date]

    return [
        {
            "date": row.get("date", ""),
            "keyword": row.get("keyword", ""),
            "score": _to_float(row.get("score")),
            "topic": row.get("topic", "") or "その他",
            "audience_segment": row.get("audience_segment", "") or "中立・不明",
            "generation_segment": row.get("generation_segment", "") or "世代不明",
        }
        for row in source_rows
    ]


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
