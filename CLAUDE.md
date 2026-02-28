# CLAUDE.md

このファイルは Claude Code がこのリポジトリで作業する際のガイドです。

## プロジェクト概要

塾の合格実績Excelファイルを自動集計・分析する Web ダッシュボード。
FastAPI + htmx + Chart.js + pandas 構成。uv でパッケージ管理。

## 開発コマンド

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動（ホットリロード）
uv run uvicorn src.goukaku_analytics.main:app --host 127.0.0.1 --port 8000 --reload
```

## ディレクトリ構成

```
src/goukaku_analytics/
├── main.py          # FastAPI ルート定義（全エンドポイント）
├── config.py        # pydantic-settings による .env 読み込み
├── loader.py        # Excel 読み込み・前処理（COL_MAP で列名正規化）
├── analysis/
│   ├── summary.py   # 合格者数・合格率・大学別ランキング・受験方式別集計
│   ├── scores.py    # 共通テスト得点分析（文理別・科目別・ヒストグラム）
│   └── trends.py    # 経年比較（複数年 DataFrame を受け取りグラフ用データ生成）
└── templates/
    ├── base.html        # 共通レイアウト（サイドバー・ドラッグ&ドロップ・Tailwind/htmx/Chart.js CDN）
    ├── dashboard.html   # ダッシュボードページ
    ├── summary.html     # 合格実績集計ページ
    ├── scores.html      # 共通テスト分析ページ
    ├── trends.html      # 経年比較ページ
    └── partials/
        ├── summary_table.html   # htmx 部分更新用：受験方式別テーブル
        └── ranking_table.html   # htmx 部分更新用：大学別ランキングテーブル
```

## 重要な設計上の決定

### Excel 列の読み込み方式

Excel のカラムヘッダーには改行・スペース・特殊文字が混在するため、
**列名ではなく位置インデックス**で読み込み、`COL_MAP` 辞書で標準名に変換している。

```python
# loader.py の COL_MAP（一部）
COL_MAP = {
    0: "No", 17: "合格", 21: "分類", 23: "大学名",
    43: "合計得点", 46: "文理区分", ...
}
```

### アップロードファイルの管理

`main.py` のグローバル変数 `_current_upload` でアップロードされたファイルを管理。
`.env` の設定ファイルよりアップロードファイルを優先して使用する。

```python
_current_upload: dict = {"path": None, "filename": None}
```

- `POST /upload`：ファイルを `%TEMP%/goukaku_analytics/` に保存し `/` にリダイレクト
- `POST /upload/clear`：`_current_upload` をリセットし `/` にリダイレクト
- Jinja2 グローバル関数 `current_filename()` でサイドバーに現在のファイル名を表示

### Jinja2 カスタム設定

```python
templates.env.globals["enumerate"] = enumerate
templates.env.globals["current_filename"] = _current_filename
templates.env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
```

### 経年比較の設定

`.env` に複数年度のパスを設定することで経年比較が有効になる。

```
EXCEL_2026=...
EXCEL_2025=...  # 追加するだけで /trends に反映される
```

## .env 設定例

```
EXCEL_2026=F:\OneDrive\AI\合格実績_sample.xlsx
# EXCEL_2025=F:\OneDrive\AI\合格実績_2025.xlsx
```

`.env` は `.gitignore` に含まれているためコミットされない。

## 依存関係

`pyproject.toml` に全て記載。`uv sync` で再現可能。
主要ライブラリ: `fastapi`, `uvicorn[standard]`, `pandas`, `openpyxl`,
`jinja2`, `pydantic-settings`, `python-multipart`
