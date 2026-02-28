import pandas as pd


def get_trend_data(year_dfs: dict[int, pd.DataFrame]) -> dict:
    """経年比較データを生成"""
    years = sorted(year_dfs.keys())
    rows = []

    for year in years:
        df = year_dfs[year]
        passed = df[df["合格"] == 1]

        total = df["No"].nunique()
        passed_count = passed["No"].nunique()

        by_category = passed.groupby("分類ラベル")["No"].nunique().to_dict()

        rows.append({
            "年度": year,
            "全生徒数": total,
            "合格者数": passed_count,
            "国立": by_category.get("国立", 0),
            "公立": by_category.get("公立", 0),
            "私立": by_category.get("私立", 0),
            "大学校": by_category.get("大学校", 0),
            "看護専門": by_category.get("看護専門", 0),
        })

    df_trend = pd.DataFrame(rows)

    return {
        "years": years,
        "rows": df_trend.to_dict(orient="records"),
        "chart": {
            "labels": [str(y) for y in years],
            "datasets": _build_datasets(df_trend, years),
        },
    }


def _build_datasets(df: pd.DataFrame, years: list[int]) -> list[dict]:
    series = [
        ("合格者数", "rgba(59,130,246,0.8)"),
        ("国立", "rgba(16,185,129,0.8)"),
        ("公立", "rgba(245,158,11,0.8)"),
        ("私立", "rgba(239,68,68,0.8)"),
    ]
    datasets = []
    for label, color in series:
        if label in df.columns:
            datasets.append({
                "label": label,
                "data": df[label].tolist(),
                "borderColor": color,
                "backgroundColor": color.replace("0.8", "0.2"),
                "tension": 0.3,
            })
    return datasets
