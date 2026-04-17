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
