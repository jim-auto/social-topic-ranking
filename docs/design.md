# Design

## Pipeline

1. `collect`: Google Trendsから急上昇ワード、関連クエリ、時系列を取得する。
2. `preprocess`: 日本語正規化、不要語除去、名詞抽出を行う。
3. `topic`: LLM分類を優先し、失敗時または未設定時はキーワード辞書で分類する。
4. `scoring`: テーマ単位でscoreを合計し、ランキングと時系列を作る。
5. `visualize`: ランキング棒グラフ、時系列折れ線グラフ、静的サイトを出力する。

## Data Contract

収集後の基本カラム:

| column | meaning |
| --- | --- |
| `date` | 対象日 |
| `keyword` | 検索ワード |
| `score` | Google Trends由来の相対人気度 |
| `source` | `trending_searches`, `related_queries:*`, `interest_over_time`, `sample` |
| `rank` | 順位がある場合の順位 |
| `related_to` | 関連クエリの元ワード |

分類後に追加されるカラム:

| column | meaning |
| --- | --- |
| `normalized_keyword` | NFKC正規化、小文字化、記号除去後の検索ワード |
| `nouns` | 抽出した名詞 |
| `topic` | 分類テーマ |
| `confidence` | 分類信頼度 |
| `classification_method` | `llm` または `keyword_fallback` |
| `matched_keywords` | fallback分類で一致した辞書キーワード |

## Notes

Google Trendsは絶対検索ボリュームを返しません。分析上のscoreは、同じ取得条件における相対値として扱います。急上昇ワードは順位しか得られないため、順位を1-100に正規化しています。

`score` は内部計算値として残し、ユーザー向けの主要指標は以下にする。

| metric | meaning |
| --- | --- |
| `interest_share_pct` | 同じ日付の全テーマ合計に対する構成比。ランキングとグラフの主指標。 |
| `attention_index` | 同じ日付の1位テーマを100とした相対指数。 |
| `share_delta_pct` | 最新期間と前期間の `interest_share_pct` 差分。 |

この方針により、Google Trendsの相対値をそのまま見せるのではなく、「全体の何%を占めるか」「1位に対してどれくらい強いか」で解釈できるようにする。

`related_queries()` の `rising` は増加率として大きな値を返すことがあるため、テーマスコアに混ぜる前に最大100へ丸めます。`top` と `interest_over_time()` はGoogle Trendsの0-100相対値を使います。

`interest_over_time()` が時間粒度の行を返した場合は、日付とキーワード単位で平均値に集約します。

## Seed Keyword Strategy

`pytrends` の急上昇ワード系エンドポイントはGoogle側の変更で失敗することがあるため、デフォルトでは `config/seed_keywords.yml` の代表検索語を起点にします。

seedキーワード収集の流れ:

1. `config/seed_keywords.yml` を読み、重複を除いた検索語リストにする。
2. `interest_over_time()` でseed検索語の時系列スコアを取得する。
3. `related_queries()` でseedから関連検索語を拡張する。
4. 取得できた検索語を通常の分類、スコアリングへ流す。

急上昇ワードを併用したい場合は、`config/settings.yml` の `google_trends.use_trending_searches` を `true` にする。

## Context-Aware Fallback

`related_queries()` 由来の行は `related_to` にseed検索語を持ちます。検索語単独で分類できない場合でも、`related_to` がテーマ辞書に一致すれば、その文脈を弱いシグナルとして使います。

例:

| keyword | related_to | inferred topic |
| --- | --- | --- |
| `ローソン` | `スイーツ` | 食（カフェ・グルメ） |
| `トモコレ` | `switch` | ゲーム |
| `ニューバランス` | `スニーカー` | ファッション |

男女推定、年代別分析、地域別分析は、分類器と設定ファイルを拡張して追加する想定です。

## Audience Signals

`config/audience.yml` の辞書を使い、検索語ごとに `audience_segment` を付与する。

このラベルは検索語の特徴を表すもので、検索した個人の性別を推定するものではない。集計用途では `audience_breakdown.csv` を使い、以下の3区分で見る。

| segment | meaning |
| --- | --- |
| `男性寄り` | メンズ、男性、ひげ、AGA、車、バイクなど男性向け文脈が強い検索語。 |
| `女性寄り` | レディース、女性、コスメ、メイク、妊娠、育児など女性向け文脈が強い検索語。 |
| `中立・不明` | 男女どちらとも判断しない検索語。 |

`メンズ` / `レディース` / `男性` / `女性` のような明示語は強いシグナルとして扱う。趣味・購買カテゴリだけで強く決めすぎないよう、曖昧な語は `中立・不明` に残す。

## Generation Signals

`config/generation.yml` の辞書を使い、検索語ごとに `generation_segment` を付与する。

これは検索した個人の年齢を推定するものではない。検索語に含まれるライフステージ文脈のラベルであり、集計上の弱いシグナルとして使う。

| segment | examples |
| --- | --- |
| `10代・学生` | 高校生、中学生、受験、部活、テスト |
| `20代` | 大学生、就活、新卒、成人式、一人暮らし |
| `30代` | 婚活、妊娠、出産、育児、保育園 |
| `40代` | 授業参観、中学受験、管理職、更年期、介護 |
| `50代以上` | 年金、老後、退職、定年、相続 |
| `世代不明` | 世代文脈が弱い検索語 |

集計結果は `generation_breakdown.csv` とサイトの `Generation Signals` に出力する。

## Site Filters

静的サイトでは `classified_keywords.csv` から最新日の `filter_records.json` を作り、ブラウザ側でRankingを再集計する。

フィルタ対象:

| filter | source column |
| --- | --- |
| `男女寄り` | `audience_segment` |
| `世代` | `generation_segment` |

フィルタは検索ワードの特徴ラベルを使う。ユーザー本人の性別や年齢として扱わず、検索語に含まれる文脈別のランキング比較に限定する。
