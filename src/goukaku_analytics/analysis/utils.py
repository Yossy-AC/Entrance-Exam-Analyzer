"""集計モジュール共通ユーティリティ"""
import json
import numpy as np
import pandas as pd


def native(val):
    """numpy 型を Python ネイティブ型に変換"""
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        return float(val)
    return val


def native_records(records: list[dict]) -> list[dict]:
    """to_dict(orient='records') の結果を全て Python ネイティブ型に変換"""
    return [{k: native(v) for k, v in row.items()} for row in records]


def json_default(obj):
    """json.dumps の default 引数用。numpy 型を変換"""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def get_filter_options(df) -> dict:
    """DataFrame からフィルタ用の選択肢を取得"""
    classrooms = sorted(
        [str(int(v)) if isinstance(v, float) else str(v)
         for v in df["教室"].dropna().unique()]
    )
    schools = sorted(
        [str(v) for v in df["学校"].dropna().unique() if str(v).strip()]
    )
    return {
        "classrooms": classrooms,
        "schools": schools,
        "bunri": ["文系", "理系"],
        "kokushi": ["国公立", "私立等", "その他"],
    }


def apply_filters(df, filters: dict):
    """URLクエリパラメータに基づきDataFrameをフィルタリング"""
    if filters.get("classroom"):
        df = df[df["教室"].apply(
            lambda x: str(int(x)) if isinstance(x, float) and not pd.isna(x) else str(x)
        ) == filters["classroom"]]
    if filters.get("school"):
        df = df[df["学校"].astype(str) == filters["school"]]
    if filters.get("bunri"):
        df = df[df["文理"] == filters["bunri"]]
    if filters.get("kokushi"):
        df = df[df["国公私"] == filters["kokushi"]]
    return df
