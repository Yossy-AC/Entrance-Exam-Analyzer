import pandas as pd

SUBJECT_MAP = {
    "英R\n": "英語R",
    "英L\n": "英語L",
    "数学１ ": "数学１",
    "数学２": "数学２",
    "国語\n": "国語",
    "物理　\n(1)": "物理",
    "化学　\n(2)": "化学",
    "生物　\n(3)": "生物",
    "地学　\n(4)": "地学",
    "物基　\n(5)": "物理基礎",
    "化基　\n(5)": "化学基礎",
    "生基　\n(5)": "生物基礎",
    "地基　\n(5)": "地学基礎",
    "世史　\n(1)": "世界史",
    "日史　\n(2)": "日本史",
    "地理　\n(3)": "地理",
    "倫理　\n(4)": "倫理",
    "政経　\n(5)": "政経",
    "地歴\n公共　\n(6)": "地歴公共",
    "情報　": "情報",
}


def _get_subject_cols(df: pd.DataFrame) -> dict[str, str]:
    """存在するカラムのみ返す"""
    return {col: label for col, label in SUBJECT_MAP.items() if col in df.columns}


def get_score_summary(df: pd.DataFrame) -> dict:
    """共通テスト得点の集計"""
    subject_cols = _get_subject_cols(df)

    # 合計得点（共通テスト受験者のみ）
    score_df = df[df["合計得点"] > 0].copy()

    # 文理別の平均合計点
    bunri_avg = (
        score_df.groupby("文理")["合計得点"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "平均点", "count": "人数"})
    )
    bunri_avg["平均点"] = bunri_avg["平均点"].round(1)

    # 科目別平均点（文理・合否別）
    subject_avgs = []
    for col, label in subject_cols.items():
        numeric_col = pd.to_numeric(df[col], errors="coerce")
        # 0点は未受験とみなし除外
        valid = df[numeric_col > 0].copy()
        valid_col = pd.to_numeric(valid[col], errors="coerce")
        if len(valid_col) > 0:
            subject_avgs.append({
                "科目": label,
                "全体平均": round(float(valid_col.mean()), 1),
                "文系平均": round(float(pd.to_numeric(valid[valid["文理"] == "文系"][col], errors="coerce").mean()), 1) if len(valid[valid["文理"] == "文系"]) > 0 else 0,
                "理系平均": round(float(pd.to_numeric(valid[valid["文理"] == "理系"][col], errors="coerce").mean()), 1) if len(valid[valid["文理"] == "理系"]) > 0 else 0,
            })

    # 得点分布（ヒストグラム用）
    bins = list(range(0, 1100, 50))
    hist_data = {}
    for bunri in ["文系", "理系"]:
        sub = score_df[score_df["文理"] == bunri]["合計得点"].dropna()
        counts, edges = _histogram(sub.tolist(), bins)
        hist_data[bunri] = {"counts": counts, "edges": [int(e) for e in edges[:-1]]}

    # 合格者 vs 不合格者の得点比較
    pass_vs_fail = []
    for label, code in [("合格", 1), ("不合格", 2)]:
        sub = score_df[score_df["合格"] == code]["合計得点"]
        if len(sub) > 0:
            pass_vs_fail.append({
                "区分": label,
                "平均点": round(float(sub.mean()), 1),
                "最大": int(sub.max()),
                "最小": int(sub.min()),
                "人数": len(sub),
            })

    return {
        "bunri_avg": bunri_avg.to_dict(orient="records"),
        "subject_avgs": subject_avgs,
        "hist_data": hist_data,
        "pass_vs_fail": pass_vs_fail,
    }


def _histogram(values: list, bins: list) -> tuple[list, list]:
    """簡易ヒストグラム計算"""
    counts = [0] * (len(bins) - 1)
    for v in values:
        for i in range(len(bins) - 1):
            if bins[i] <= v < bins[i + 1]:
                counts[i] += 1
                break
    return counts, bins
