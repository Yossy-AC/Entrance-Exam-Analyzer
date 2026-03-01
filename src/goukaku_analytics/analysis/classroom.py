import pandas as pd

from .utils import native_records


def get_classroom_summary(df: pd.DataFrame) -> dict:
    """教室別の生徒数・受験数・合格率・分類別合格数を集計"""
    classrooms = sorted(df["教室"].dropna().unique().tolist(), key=lambda x: str(x))

    rows = []
    for room in classrooms:
        sub = df[df["教室"] == room]
        total_students = int(sub["No"].nunique())
        total_exams = len(sub)
        passed_count = int((sub["合格"] == 1).sum())
        failed_count = int((sub["合格"] == 2).sum())
        pass_rate = round(passed_count / total_exams * 100, 1) if total_exams > 0 else 0.0

        # 分類別合格数
        passed_sub = sub[sub["合格"] == 1]
        kokukoritsu = int(passed_sub[passed_sub["国公私"] == "国公立"]["No"].nunique())
        shiritsu = int(passed_sub[passed_sub["国公私"] == "私立等"]["No"].nunique())

        rows.append({
            "教室": str(int(room)) if isinstance(room, float) else str(room),
            "生徒数": total_students,
            "受験数": total_exams,
            "合格件数": passed_count,
            "不合格件数": failed_count,
            "合格率": pass_rate,
            "国公立合格": kokukoritsu,
            "私立等合格": shiritsu,
        })

    # チャート用データ
    chart = {
        "labels": [r["教室"] for r in rows],
        "datasets": [
            {
                "label": "国公立合格",
                "data": [r["国公立合格"] for r in rows],
                "backgroundColor": "rgba(16,185,129,0.7)",
                "borderColor": "rgba(16,185,129,1)",
                "borderWidth": 1,
                "borderRadius": 4,
            },
            {
                "label": "私立等合格",
                "data": [r["私立等合格"] for r in rows],
                "backgroundColor": "rgba(59,130,246,0.7)",
                "borderColor": "rgba(59,130,246,1)",
                "borderWidth": 1,
                "borderRadius": 4,
            },
        ],
    }

    return {
        "rows": native_records(rows),
        "chart": chart,
        "total_classrooms": len(classrooms),
    }
