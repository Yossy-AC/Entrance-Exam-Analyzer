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
    4: "生徒名",
    5: "セイトメイ",
    6: "性別",
    7: "学校",
    8: "学科",
    9: "JA併用",
    10: "通塾履歴",
    11: "VIP",
    12: "部活",
    13: "承諾書",
    14: "撮影",
    15: "合格アンケ",
    16: "更新日",
    17: "合格",
    18: "合格状態",
    19: "進学先決定",
    20: "進学先状態",
    21: "分類",
    22: "分類補足",
    23: "大学名",
    24: "学部名",
    25: "学科名",
    26: "志望順位",
    27: "方式",
    28: "方式補足",
    29: "発表日",
    30: "備考",
    31: "分類2",
    32: "分類2補足",
    33: "大学名2",
    34: "学部名2",
    35: "学科名2",
    36: "備考2",
    37: "分類3",
    38: "分類3補足",
    39: "大学名3",
    40: "学部名3",
    41: "学科名3",
    42: "備考3",
    43: "合計得点",
    44: "得点率",
    45: "満点",
    46: "文理区分",
    47: "英R",
    48: "英L",
    49: "数学1",
    50: "数学2",
    51: "国語",
    52: "物理",
    53: "化学",
    54: "生物",
    55: "地学",
    56: "物理基礎",
    57: "化学基礎",
    58: "生物基礎",
    59: "地学基礎",
    60: "世界史",
    61: "日本史",
    62: "地理",
    63: "倫理",
    64: "政経",
    65: "地歴公共",
    66: "情報",
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
    ws = wb.worksheets[1]

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
