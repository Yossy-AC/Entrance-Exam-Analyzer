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
# 2026-03-01: Excel から「氏名」(旧4列目)・「ｼﾒｲ」(旧5列目) を削除したため、
# インデックス6以降を全て-2シフト済み
COL_MAP = {
    0: "No", 15: "合格", 19: "分類", 21: "大学名",
    41: "合計得点", 44: "文理区分", ...
}
```

### Excelファイル構造

- ファイルの **シート0（最初のシート）** のみを読み込み使用する
- ヘッダー行は自動検出（`_find_header_row_idx()` で "No" を含む行を探索）
- データは ヘッダー行の直下から開始

### アップロードファイルの管理

`main.py` のグローバル変数 `_current_upload` でアップロードされたファイルを管理。
`.env` の設定ファイルよりアップロードファイルを優先して使用する。

```python
_current_upload: dict = {"path": None, "filename": None}
```

- `POST /upload`：ファイルを `%TEMP%/goukaku_analytics/` に保存し `{"ok": true}` を返す（200 JSON）
  - クライアント側（XMLHttpRequest）が 200 を受け取ってから `window.location.href = '/'` でリダイレクト
  - ※旧実装は 303 リダイレクトを返していたが、`fetch` / `XMLHttpRequest` との組み合わせで `net::ERR_FAILED` が発生するため変更
- `POST /upload/clear`：`_current_upload` をリセット、プロジェクトルートの `EntranceExam_Results_*.xlsx` を削除し `/` にリダイレクト
- Jinja2 グローバル関数 `current_filename()` でサイドバーに現在のファイル名を表示
- サイドバーには削除ボタン付きで現在のファイル名を表示、下部にアップロードエリア（ドラッグ&ドロップ or クリック）を配置

### Jinja2 カスタム設定

```python
templates.env.globals["enumerate"] = enumerate
templates.env.globals["current_filename"] = _current_filename
templates.env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
```

### ダッシュボード構成

**上部（統計カード）**：在籍人数、総受験数、合格率、データ更新日

**中段（グラフ）**：
- 国公立大 受験方式別合格者数（棒グラフ）
- 私立大 受験方式別合格者数（棒グラフ）

**下部（テーブル）**：
- 左：分類別集計一覧（国立/公立/私立等の合格者数）
- 右：受験結果（出願・合格・不合格・合計の件数）

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
- その他のページ（`/summary`, `/scores`, `/trends`）：`/` にリダイレクト

## 既知の制約

- **FastAPI 0.134.0 + Starlette 0.52.1 の HTTPException**:
  `fastapi.HTTPException` と `starlette.HTTPException` が別クラスになったため、
  ルート関数から HTTPException を raise してもデフォルトハンドラーが機能しない場合がある。
  このプロジェクトでは HTTPException を使わず、ルート内で `None` チェックとリダイレクトで代替している。

- **ブラウザアップロード `net::ERR_FAILED`（未解決）**:
  Chrome 145 + Python 3.14.3 + Windows 環境で、ブラウザの drag&drop / ファイル選択によるアップロードが
  `net::ERR_FAILED` で失敗する事象が確認されている。
  - サーバーログに `POST /upload` が全く記録されない（リクエストがサーバーに到達していない）
  - `fetch` API・`XMLHttpRequest` どちらでも同様に失敗
  - 試した変更: `shutil.copyfileobj` → `await file.read()` + `dest.write_bytes()`、303 → 200 JSON レスポンス
  - 調査継続中。`.env` でファイルパスを直接指定する方法は正常動作する

- **pandas numpy 型の JSON シリアライズエラー**:
  pandas の `.sum()` が返す `numpy.int64` 型は、Jinja2 テンプレート内の `tojson` フィルターでシリアライズ失敗し `Internal Server Error` が発生する。
  **対策**: 集計関数の戻り値は明示的に `int()` や `float()` で Python ネイティブ型に変換する。
  ```python
  # 修正例
  passed = int((df["合格"] == 1).sum())  # numpy.int64 → int
  ```

## Excelファイル命名規則

`EntranceExam_Results_YYYY.xlsx` の形式を使用する（年度のみ変更）。

## 依存関係

`pyproject.toml` に全て記載。`uv sync` で再現可能。
主要ライブラリ: `fastapi`, `uvicorn[standard]`, `pandas`, `openpyxl`,
`jinja2`, `pydantic-settings`, `python-multipart`
