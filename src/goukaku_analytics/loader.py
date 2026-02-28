from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime

# 分類コードのマッピング
CATEGORY_LABELS = {
    1: "国立", 2: "公立", 3: "大学校", 4: "私立", 5: "看護専門",
    6: "その他専門", 7: "専門職大学", 8: "短大", 9: "就職", 10: "浪人", 11: "不明",
}

# 合否コードのマッピング
PASS_LABELS = {0: "出願", 1: "合格", 2: "不合格"}

# 列インデックス → 標準列名のマッピング（固定位置）
COL_MAP = {
    0: "No",
    1: "生徒コード",
    2: "教室",
    3: "学年",
    4: "性別",
    5: "学校",
    6: "学科",
    7: "JA併用",
    8: "通塾履歴",
    9: "VIP",
    10: "部活",
    11: "承諾書",
    12: "撮影",
    13: "合格アンケ",
    14: "更新日",
    15: "合格",
    16: "合格状態",
    17: "進学先決定",
    18: "進学先状態",
    19: "分類",
    20: "分類補足",
    21: "大学名",
    22: "学部名",
    23: "学科名",
    24: "志望順位",
    25: "方式",
    26: "方式補足",
    27: "発表日",
    28: "備考",
    29: "分類2",
    30: "分類2補足",
    31: "大学名2",
    32: "学部名2",
    33: "学科名2",
    34: "備考2",
    35: "分類3",
    36: "分類3補足",
    37: "大学名3",
    38: "学部名3",
    39: "学科名3",
    40: "備考3",
    41: "合計得点",
    42: "得点率",
    43: "満点",
    44: "文理区分",
    45: "英R",
    46: "英L",
    47: "数学1",
    48: "数学2",
    49: "国語",
    50: "物理",
    51: "化学",
    52: "生物",
    53: "地学",
    54: "物理基礎",
    55: "化学基礎",
    56: "生物基礎",
    57: "地学基礎",
    58: "世界史",
    59: "日本史",
    60: "地理",
    61: "倫理",
    62: "政経",
    63: "地歴公共",
    64: "情報",
}

SUBJECT_COLUMNS = [
    "英R", "英L", "数学1", "数学2", "国語",
    "物理", "化学", "生物", "地学",
    "物理基礎", "化学基礎", "生物基礎", "地学基礎",
    "世界史", "日本史", "地理", "倫理", "政経", "地歴公共", "情報",
]


def _find_header_row_idx(ws) -> int:
    """'No' が含まれるヘッダー行の行番号(1始まり)を返す"""
    for i, row in enumerate(ws.iter_rows(max_row=20, values_only=True)):
        if any(str(v).strip() == "No" for v in row if v is not None):
            return i + 1  # 1始まりに変換
    return 5


def load_data(path: Path) -> pd.DataFrame:
    """Excelからメインデータシートを読み込みDataFrameとして返す"""
    wb = load_workbook(path, data_only=True)
    ws = wb.worksheets[0]

    header_row = _find_header_row_idx(ws)
    data_start = header_row + 1

    rows = []
    for row in ws.iter_rows(min_row=data_start, values_only=True):
        rows.append(list(row))

    max_cols = max(len(r) for r in rows) if rows else 70
    col_names = [COL_MAP.get(i, f"col_{i}") for i in range(max_cols)]

    # 短い行をパディング
    padded = [r + [None] * (max_cols - len(r)) for r in rows]
    df = pd.DataFrame(padded, columns=col_names[:max_cols])

    # 空行（No が None）を除外
    df = df.dropna(subset=["No"]).copy()
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
    df = df.dropna(subset=["No"]).copy()
    df["No"] = df["No"].astype(int)

    # 合否フラグ
    df["合格"] = pd.to_numeric(df["合格"], errors="coerce").fillna(0).astype(int)
    df["合格ラベル"] = df["合格"].map(PASS_LABELS).fillna("不明")

    # 分類ラベル
    df["分類"] = pd.to_numeric(df["分類"], errors="coerce")
    df["分類ラベル"] = df["分類"].map(CATEGORY_LABELS).fillna("不明")

    # 国公私区分
    df["国公私"] = df["分類"].apply(
        lambda x: "国公立" if x in [1, 2, 3] else ("私立等" if x in [4, 5, 6, 7, 8] else "その他")
    )

    # 文理区分
    df["文理区分"] = pd.to_numeric(df["文理区分"], errors="coerce")
    df["文理"] = df["文理区分"].map({1: "文系", 2: "理系"}).fillna("不明")

    # 共通テスト得点
    df["合計得点"] = pd.to_numeric(df["合計得点"], errors="coerce")
    df["得点率"] = pd.to_numeric(df["得点率"], errors="coerce")

    # 科目得点を数値変換
    for col in SUBJECT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def get_update_date(path: Path) -> str:
    """Excelから更新日を取得"""
    try:
        wb = load_workbook(path, data_only=True)
        ws = wb.worksheets[1]
        for row in ws.iter_rows(max_row=5, values_only=True):
            for i, val in enumerate(row):
                if val == "更新日" and i + 1 < len(row):
                    date_val = row[i + 1]
                    if isinstance(date_val, datetime):
                        return date_val.strftime("%Y-%m-%d")
                    return str(date_val)
    except Exception:
        pass
    return "不明"


def load_all_years(year_paths: dict[int, Path]) -> dict[int, pd.DataFrame]:
    """複数年度のデータを読み込む"""
    result = {}
    for year, path in year_paths.items():
        try:
            result[year] = load_data(path)
        except Exception as e:
            print(f"Warning: {year}年度データの読み込みに失敗 ({e})")
    return result
