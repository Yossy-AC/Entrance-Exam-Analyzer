import pandas as pd

from .utils import native_records

PREF_LABELS = {1: "第1志望", 2: "第2志望", 3: "第3志望以降"}


def get_preference_summary(df: pd.DataFrame) -> dict:
    """進学先決定（志望順位別）の分析。生徒単位でカウント。"""
    # 生徒ごとに進学先決定の最小値（最も高い志望順位）を採用
    decided_rows = df[df["進学先決定"].isin([1, 2, 3])].copy()
    student_pref = decided_rows.groupby("No")["進学先決定"].min().reset_index()

    total_decided = len(student_pref)
    total_students = int(df["No"].nunique())

    # 志望順位別の人数
    dist = []
    for code, label in PREF_LABELS.items():
        count = int((student_pref["進学先決定"] == code).sum())
        dist.append({
            "志望": label,
            "人数": count,
            "割合": round(count / total_decided * 100, 1) if total_decided > 0 else 0.0,
        })

    # 第1志望合格率（決定者のうち第1志望の割合）
    first_choice_count = int((student_pref["進学先決定"] == 1).sum())
    first_choice_rate = round(first_choice_count / total_decided * 100, 1) if total_decided > 0 else 0.0

    # 国公私別 × 志望順位（進学先決定行から生徒ごとの国公私を取得）
    student_kokushi = decided_rows.groupby("No").agg(
        進学先決定=("進学先決定", "min"),
        国公私=("国公私", "first"),
    ).reset_index()

    kokushi_pref = []
    for kokushi in ["国公立", "私立等"]:
        sub = student_kokushi[student_kokushi["国公私"] == kokushi]
        if len(sub) == 0:
            continue
        for code, label in PREF_LABELS.items():
            count = int((sub["進学先決定"] == code).sum())
            kokushi_pref.append({
                "区分": kokushi,
                "志望": label,
                "人数": count,
            })

    # ドーナツチャート用データ
    chart = {
        "labels": [d["志望"] for d in dist],
        "data": [d["人数"] for d in dist],
        "colors": ["rgba(16,185,129,0.8)", "rgba(59,130,246,0.8)", "rgba(245,158,11,0.8)"],
    }

    return {
        "total_decided": total_decided,
        "total_students": total_students,
        "undecided": total_students - total_decided,
        "first_choice_rate": first_choice_rate,
        "first_choice_count": first_choice_count,
        "dist": native_records(dist),
        "kokushi_pref": native_records(kokushi_pref),
        "chart": chart,
    }
