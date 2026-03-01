import pandas as pd

from .utils import native_records

# 方式コードのラベル（国公立用）
METHOD_LABELS_KOKURITSU = {
    1: "前期",
    2: "中期",
    3: "後期",
    4: "学校推薦",
    5: "国公立総合",
}

# 方式コードのラベル（私立用）
METHOD_LABELS_SHIRITSU = {
    1: "一般",
    2: "共通テスト利用",
    3: "指定校",
    4: "公募",
    5: "私立総合",
}


def _add_method_columns(df: pd.DataFrame) -> pd.DataFrame:
    """方式コード→方式名の変換列を追加。国公私別にラベルを割り当て（コピーを返す）"""
    df = df.copy()
    df["方式コード"] = pd.to_numeric(df["方式"], errors="coerce")

    def get_method_label(row):
        code = row["方式コード"]
        kokushi = row["国公私"]

        if pd.isna(code):
            return str(row["方式"]) if pd.notna(row["方式"]) else "不明"

        code = int(code)
        if kokushi == "国公立":
            return METHOD_LABELS_KOKURITSU.get(code, str(code))
        else:  # 私立等
            return METHOD_LABELS_SHIRITSU.get(code, str(code))

    df["方式名"] = df.apply(get_method_label, axis=1)
    return df


def get_pass_summary(df: pd.DataFrame) -> dict:
    """合格者数・合格率の集計"""
    passed = df[df["合格"] == 1]

    by_category_passed = (
        passed.groupby("分類ラベル")["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数"})
    )

    by_category_all = (
        df.groupby("分類ラベル").size()
        .reset_index(name="受験数")
    )

    by_category = (
        by_category_passed.merge(by_category_all, on="分類ラベル")
        .rename(columns={"分類ラベル": "分類"})
        .sort_values("合格者数", ascending=False)
        [["分類", "合格者数", "受験数"]]
    )

    by_kokushi = (
        passed.groupby("国公私")["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数", "国公私": "区分"})
    )

    total_exams = len(df)
    passed_count = int((df["合格"] == 1).sum())

    return {
        "total_students": int(df["No"].nunique()),
        "passed_count": passed_count,
        "total_exams": total_exams,
        "pass_rate": round(passed_count / total_exams * 100, 1) if total_exams > 0 else 0.0,
        "by_category": native_records(by_category.to_dict(orient="records")),
        "by_kokushi": native_records(by_kokushi.to_dict(orient="records")),
    }


def get_university_ranking(df: pd.DataFrame, top_n: int = 20) -> list[dict]:
    """大学別合格者数ランキング"""
    passed = df[df["合格"] == 1]

    if "大学名" not in passed.columns:
        return []

    passed = passed[passed["大学名"].notna() & (passed["大学名"].astype(str).str.strip() != "")]

    ranking = (
        passed.groupby(["大学名", "分類ラベル"])["No"]
        .nunique()
        .reset_index()
        .rename(columns={"No": "合格者数", "分類ラベル": "分類"})
        .sort_values("合格者数", ascending=False)
        .head(top_n)
    )
    return native_records(ranking.to_dict(orient="records"))


def get_method_summary(df: pd.DataFrame) -> list[dict]:
    """受験方式別の出願・合否件数集計"""
    if "方式" not in df.columns:
        return []

    df = _add_method_columns(df)
    result = (
        df.groupby(["方式名", "合格ラベル"])
        .size()
        .reset_index(name="件数")
        .rename(columns={"合格ラベル": "合否"})
        .sort_values(["方式名", "合否"])
    )
    return native_records(result.to_dict(orient="records"))


def get_method_by_kokushi(df: pd.DataFrame) -> dict:
    """国公立・私立別に、受験方式別の合格者数を集計"""
    if "方式" not in df.columns:
        return {"国公立": [], "私立等": []}

    df = _add_method_columns(df)
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
        result[kokushi] = native_records(agg.to_dict(orient="records"))

    return result


def get_exam_result_summary(df: pd.DataFrame) -> dict:
    """合格/不合格の結果集計（出願件数ベース）"""
    return {
        "total": int(len(df)),
        "applied": int((df["合格"] == 0).sum()),
        "passed": int((df["合格"] == 1).sum()),
        "failed": int((df["合格"] == 2).sum()),
    }
