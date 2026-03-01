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

> **Windows の bash (Git Bash) で `uv` が見つからない場合**：
> `$USERPROFILE/.local/bin/uv run uvicorn ...` のようにフルパスで指定する。

## ディレクトリ構成

```
src/goukaku_analytics/
├── main.py          # FastAPI ルート定義（全エンドポイント）
├── config.py        # pydantic-settings による .env 読み込み
├── loader.py        # Excel 読み込み・前処理（COL_MAP で列名正規化）
├── analysis/
│   ├── utils.py       # 共通ユーティリティ（numpy型変換、フィルタ処理）
│   ├── summary.py     # 合格者数・合格率・大学別ランキング・受験方式別集計
│   ├── scores.py      # 共通テスト得点分析（文理別・科目別・ヒストグラム）
│   ├── trends.py      # 経年比較（複数年 DataFrame を受け取りグラフ用データ生成）
│   ├── classroom.py   # 教室別分析（教室ごとの生徒数・合格率・国公私別）
│   └── preference.py  # 志望順位分析（進学先決定ベース・第1志望合格率）
└── templates/
    ├── base.html          # 共通レイアウト（サイドバー・ナビ・Tailwind/htmx/Chart.js CDN）
    ├── dashboard.html     # ダッシュボードページ
    ├── summary.html       # 合格実績集計ページ
    ├── scores.html        # 共通テスト分析ページ
    ├── classroom.html     # 教室別分析ページ
    ├── preference.html    # 志望順位分析ページ
    ├── trends.html        # 経年比較ページ
    └── partials/
        ├── filter_bar.html      # 共通フィルタバー（教室・学校・文理・国公私）
        ├── summary_table.html   # htmx 部分更新用：受験方式別テーブル
        └── ranking_table.html   # htmx 部分更新用：大学別ランキングテーブル
```

## 重要な設計上の決定

### 受験方式ラベル（国公私別）

「方式」列のコード値は分類によって異なる意味を持つため、分類別にラベルを定義している。

**国公立（分類1, 2）**:
- 1: 前期
- 2: 中期
- 3: 後期
- 4: 学校推薦
- 5: 国公立総合

**私立等（分類4など）**:
- 1: 一般
- 2: 共通テスト利用
- 3: 指定校
- 4: 公募
- 5: 私立総合

`_add_method_columns()` で国公私に応じたラベルを自動割り当て。

### Excel 列の読み込み方式

Excel のカラムヘッダーには改行・スペース・特殊文字が混在するため、
**列名ではなく位置インデックス**で読み込み、`COL_MAP` 辞書で標準名に変換している。

```python
# loader.py の COL_MAP（一部）
# 実Excelに「分類2補足」「分類3補足」列は存在しないため除外済み
COL_MAP = {
    0: "No", 2: "教室", 15: "合格", 17: "進学先決定",
    19: "分類", 21: "大学名", 24: "志望順位", 25: "方式",
    39: "合計得点", 42: "文理区分", ...
}
```

### Excelファイル構造

- ファイルの **シート0（最初のシート）** のみを読み込み使用する
- ヘッダー行は自動検出（`_find_header_row_idx()` で "No" を含む行を探索）
- データは ヘッダー行の直下から開始

### 合格率の計算

**件数ベース**: `合格件数 ÷ 総受験件数 × 100`
- 合格=0（出願/結果待ち）、合格=1（合格）、合格=2（不合格）の全件を分母に含める
- ユニーク生徒数ではなく受験件数で算出

### フィルタ機能

URLクエリパラメータ方式（ページリロード）。

- 対応パラメータ: `classroom`, `school`, `bunri`, `kokushi`
- `apply_filters()` in `analysis/utils.py` で一括適用
- フィルタ選択肢は `get_filter_options()` でDataFrameから動的生成
- `partials/filter_bar.html` を各テンプレートに include

### 志望順位分析

- `進学先決定` 列（1=第1志望, 2=第2志望, 3=第3志望以降）を使用
- 1生徒に複数行あるため、生徒ごとの最小値（最上位志望）で集計
- `志望順位` 列は現在全て0のため未使用

### アップロードファイルの管理

`main.py` のグローバル変数 `_current_upload` でアップロードされたファイルを管理。
`.env` の設定ファイルよりアップロードファイルを優先して使用する。

```python
_current_upload: dict = {"path": None, "filename": None}
```

- `POST /upload`：ファイルを `%TEMP%/goukaku_analytics/` に保存し `{"ok": true}` を返す（200 JSON）
- `POST /upload/clear`：`_current_upload` をリセット、プロジェクトルートの `EntranceExam_Results_*.xlsx` を削除し `/` にリダイレクト
- Jinja2 グローバル関数 `current_filename()` でサイドバーに現在のファイル名を表示

### Jinja2 カスタム設定

```python
templates.env.globals["enumerate"] = enumerate
templates.env.globals["current_filename"] = _current_filename
templates.env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False, default=json_default)
```

### ダッシュボード構成

**フィルタバー**: 教室・学校・文理・国公私で絞り込み

**統計カード**: 在籍人数、総受験数、合格率（件数ベース）、データ更新日

**グラフ**: 国公立大/私立大 受験方式別合格者数（棒グラフ）

**テーブル**: 分類別集計一覧 + 受験結果（出願・合格・不合格・合計）

### 経年比較の設定

`.env` に複数年度のパスを設定することで経年比較が有効になる。

```
EXCEL_2026=...
EXCEL_2025=...  # 追加するだけで /trends に反映される
```

## .env 設定例

```
EXCEL_2026=F:\path\to\results_2026.xlsx
# EXCEL_2025=F:\path\to\results_2025.xlsx
```

`.env` は `.gitignore` に含まれているためコミットされない。

> **注意**: `.env` のパスに日本語を含む場合、Python の `Path.exists()` が正しく機能せずファイルが見つからない扱いになる。
> Excelファイル名・パスは **ASCII のみ** を使うこと。
>
> ブラウザのドラッグ&ドロップアップロード機能は環境によっては動作しない（未解決）。
> `.env` でファイルパスを直接指定することを推奨する。

## データ未設定時の挙動

`.env` が未設定かつファイル未アップロードの場合：

- `/` (ダッシュボード)：「データファイルが読み込まれていません」メッセージを表示
- その他のページ：`/` にリダイレクト

## 既知の制約

- **FastAPI 0.134.0 + Starlette 0.52.1 の HTTPException**:
  `fastapi.HTTPException` と `starlette.HTTPException` が別クラスになったため、
  HTTPException を使わず、ルート内で `None` チェックとリダイレクトで代替している。

- **ブラウザアップロード `net::ERR_FAILED`（未解決）**:
  Chrome 145 + Python 3.14.3 + Windows 環境で、ブラウザのアップロードが失敗する。
  `.env` でファイルパスを直接指定する方法は正常動作する。

- **pandas numpy 型の JSON シリアライズエラー**:
  `analysis/utils.py` の `native()` / `native_records()` / `json_default()` で対策済み。
  集計関数の戻り値は明示的に `int()` / `float()` で変換すること。

## Excelファイル命名規則

`EntranceExam_Results_YYYY.xlsx` の形式を使用する（年度のみ変更）。

## 依存関係

`pyproject.toml` に全て記載。`uv sync` で再現可能。
主要ライブラリ: `fastapi`, `uvicorn[standard]`, `pandas`, `openpyxl`,
`jinja2`, `pydantic-settings`, `python-multipart`
