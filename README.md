# social-topic-ranking

検索エンジンのトレンドデータを使い、人々の関心をテーマ単位でランキング化するPythonプロジェクトです。SNS投稿やWeb記事ではなく、検索行動を入力にすることで、より本音に近い興味関心の構造を見ます。

## 構成

```text
social-topic-ranking/
├── data/
│   ├── raw/
│   └── sample_trends.csv
├── src/
│   ├── collect/
│   ├── preprocess/
│   ├── topic/
│   ├── scoring/
│   └── visualize/
├── config/
├── outputs/
└── docs/
```

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Python 3.10以上を想定しています。日本語の名詞抽出はSudachiPyを優先し、利用できない場合はfugashi、最後に正規表現ベースの抽出へfallbackします。

## 実行

Google Trendsから取得して実行:

```bash
python -m src.main --period daily
```

seedキーワードを明示して取得:

```bash
python -m src.main --period daily --seeds config/seed_keywords.yml
```

少数のseedだけで接続確認:

```bash
python -m src.main --period daily --seed-limit 5
```

サンプルデータで実行:

```bash
python -m src.main --input data/sample_trends.csv
```

出力は `outputs/` に保存されます。

- `classified_keywords.csv`: 検索ワードごとの正規化、名詞、テーマ分類
- `theme_ranking.csv`: 最新期間のテーマランキングTop20
- `theme_timeseries.csv`: 日次または週次のテーマ別スコア
- `theme_ranking.png`: 棒グラフ
- `theme_timeseries.png`: 折れ線グラフ

## Google Trends取得

`pytrends` を使って日本のデータを取得します。

- seedキーワード: `config/seed_keywords.yml`
- 関連クエリ: `related_queries()`
- 時系列: `interest_over_time()`
- 急上昇ワード: `trending_searches(pn="japan")`

現在のデフォルトは、`config/seed_keywords.yml` の検索語を起点に、時系列と関連クエリを取得する方式です。`pytrends` の急上昇ワード系エンドポイントはGoogle側の変更で不安定なため、`config/settings.yml` では `use_trending_searches: false` にしています。

急上昇ワード一覧を使う場合、Google Trendsは順位リストとして返すため、このプロジェクトでは順位を1-100の相対スコアへ変換します。関連クエリと時系列はGoogle Trendsが返す相対値を使います。

## seedキーワード

`config/seed_keywords.yml` でテーマ別に初期検索語を管理します。急上昇ワードAPIが使えない場合でも、代表語から `interest_over_time` と `related_queries` を取得できます。

設定例:

```yaml
seed_keywords:
  ゲーム:
    - ゲーム
    - switch
    - steam
  お金（投資・節約）:
    - NISA
    - 投資
    - 株価
```

## テーマ管理

テーマとfallback用キーワードは `config/themes.yml` で管理します。

現在のテーマ:

- 恋愛
- 美容・メイク
- ファッション
- 食（カフェ・グルメ）
- 旅行
- 芸能・推し
- アニメ・漫画
- ゲーム
- 仕事・キャリア
- お金（投資・節約）
- 日常・雑談
- その他

## 分類

分類は `config/settings.yml` の設定に従います。

- LLM分類: `classification.llm.enabled: true` で有効化
- fallback分類: `config/themes.yml` のキーワード辞書で分類

LLM分類をOpenAIで使う場合は、追加で `openai` パッケージを入れ、`OPENAI_API_KEY` を設定してください。モデル名は `OPENAI_TOPIC_MODEL` または `classification.llm.model` で指定できます。

## スコアリング

検索ワードの `score` をそのワードの検索人気度として扱います。

```text
テーマスコア = 同一テーマに分類された検索ワードscoreの合計
```

ただし、`score` はGoogle Trends由来の内部計算値なので、人間が読む指標としては次の2つを主に使います。

| column | meaning |
| --- | --- |
| `interest_share_pct` | その日の検索関心全体に占める割合。例: `24.5` は全体の24.5%。 |
| `attention_index` | 1位テーマを100とした相対指数。例: `50` は1位の半分くらいの強さ。 |
| `share_delta_pct` | 前期間からの関心シェア差分。例: `+3.2` は3.2ポイント増。 |

`theme_ranking.csv` とグラフは `interest_share_pct` を中心に見ます。`score` は再集計やデバッグ用に残しています。

## 男女寄りシグナル

検索ワードごとに `audience_segment` を出力します。

| value | meaning |
| --- | --- |
| `男性寄り` | `メンズ`, `男性`, `彼女`, `ひげ`, `AGA`, `車`, `バイク` などの語が強い検索語。 |
| `女性寄り` | `レディース`, `女性`, `彼氏`, `コスメ`, `メイク`, `妊娠`, `育児` などの語が強い検索語。 |
| `中立・不明` | 検索語だけでは男女寄りを判断しない検索語。 |

これは検索語レベルの弱いシグナルであり、検索した個人の性別を推定するものではありません。集計結果は `outputs/audience_breakdown.csv` とサイトの `Audience Signals` に出力されます。

## 世代シグナル

検索ワードごとに `generation_segment` も出力します。

| value | meaning |
| --- | --- |
| `10代・学生` | `高校生`, `中学生`, `受験`, `部活`, `テスト` など学生文脈が強い検索語。 |
| `20代` | `大学生`, `就活`, `新卒`, `成人式`, `一人暮らし` など若年成人文脈が強い検索語。 |
| `30代` | `婚活`, `妊娠`, `出産`, `育児`, `保育園`, `マイホーム` などの文脈。 |
| `40代` | `授業参観`, `中学受験`, `管理職`, `更年期`, `介護` などの文脈。 |
| `50代以上` | `年金`, `老後`, `退職`, `定年`, `相続`, `孫` などの文脈。 |
| `世代不明` | 検索語だけでは世代文脈を判断しない検索語。 |

これは検索した個人の年齢を推定するものではありません。検索語に含まれるライフステージ文脈の集計です。集計結果は `outputs/generation_breakdown.csv` とサイトの `Generation Signals` に出力されます。

## 追加テーマ

女性向けに寄りすぎないよう、以下のテーマを追加しています。

- メンズ美容・身だしなみ
- スポーツ
- 筋トレ・フィットネス
- 健康・医療
- 車・バイク
- ガジェット・家電
- 学び・資格
- 住まい・暮らし
- 育児・家庭
- 政治・社会
- ペット
- アダルト・性
