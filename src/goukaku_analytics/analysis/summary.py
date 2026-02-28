import pandas as pd

# 方式コードのラベル（国公立・私立共通で使えるように両方定義）
METHOD_LABELS = {
    1: "一般/前期",
    2: "中期/共通テスト",
    3: "後期",
    4: "公募/学校推薦",
    5: "総合型/看護推薦",
    6: "その他",
    10: "浪人",
}


def get_pass_summary(df: pd.DataFrame) -> dict:
    """合格者数・合格率の集計"""
    passed = df[df["合格"] == 1]

    by_category = (
        passed.groupby("分類ラベル")["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数", "分類ラベル": "分類"})
        .sort_values("合格者数", ascending=False)
    )

    by_kokushi = (
        passed.groupby("国公私")["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数", "国公私": "区分"})
    )

    all_students = df["No"].nunique()
    passed_students = passed["No"].nunique()
    pass_rate = round(passed_students / all_students * 100, 1) if all_students > 0 else 0

    return {
        "total_students": all_students,
        "passed_students": passed_students,
        "pass_rate": pass_rate,
        "by_category": by_category.to_dict(orient="records"),
        "by_kokushi": by_kokushi.to_dict(orient="records"),
    }


def get_university_ranking(df: pd.DataFrame, top_n: int = 20) -> list[dict]:
    """大学別合格者数ランキング"""
    passed = df[df["合格"] == 1]

    # loader.py で "大学名" に統一済み
    if "大学名" not in passed.columns:
        return []

    # 大学名が空でない行のみ
    passed = passed[passed["大学名"].notna() & (passed["大学名"].astype(str).str.strip() != "")]

    ranking = (
        passed.groupby(["大学名", "分類ラベル"])["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数", "分類ラベル": "分類"})
        .sort_values("合格者数", ascending=False)
        .head(top_n)
    )
    return ranking.to_dict(orient="records")


def get_method_summary(df: pd.DataFrame) -> list[dict]:
    """受験方式別の出願・合否件数集計"""
    if "方式" not in df.columns:
        return []

    df = df.copy()
    df["方式コード"] = pd.to_numeric(df["方式"], errors="coerce")
    df["方式名"] = df["方式コード"].map(METHOD_LABELS).fillna(df["方式"].astype(str))

    result = (
        df.groupby(["方式名", "合格ラベル"])
        .size()
        .reset_index(name="件数")
        .rename(columns={"合格ラベル": "合否"})
        .sort_values(["方式名", "合否"])
    )
    return result.to_dict(orient="records")


def get_method_by_kokushi(df: pd.DataFrame) -> dict:
    """国公立・私立別に、受験方式別の合格者数を集計"""
    if "方式" not in df.columns:
        return {"国公立": [], "私立等": []}

    df = df.copy()
    df["方式コード"] = pd.to_numeric(df["方式"], errors="coerce")
    df["方式名"] = df["方式コード"].map(METHOD_LABELS).fillna(df["方式"].astype(str))

    # 合格者のみ
    passed = df[df["合格"] == 1]

    result = {}
    for kokushi in ["国公立", "私立等"]:
        sub = passed[passed["国公私"] == kokushi]
        agg = (
            sub.groupby("方式名")["No"]
            .nunique()
            .reset_index()
            .rename(columns={"No": "合格者数"})
            .sort_values("合格者数", ascending=False)
        )
        result[kokushi] = agg.to_dict(orient="records")

    return result


def get_exam_result_summary(df: pd.DataFrame) -> dict:
    """合格/不合格の結果集計（出願件数ベース）"""
    passed = int((df["合格"] == 1).sum())
    failed = int((df["合格"] == 2).sum())
    applied = int((df["合格"] == 0).sum())
    total = int(len(df))

    return {
        "total": total,
        "applied": applied,
        "passed": passed,
        "failed": failed,
    }
