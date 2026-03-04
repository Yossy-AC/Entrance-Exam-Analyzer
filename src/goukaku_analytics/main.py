import os
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import json
import logging
import re
import tempfile

from .config import settings
from .loader import load_data, get_update_date, load_all_years
from .analysis.utils import json_default, get_filter_options, apply_filters
from .analysis.summary import (
    get_pass_summary, get_university_ranking, get_method_summary,
    get_method_by_kokushi, get_exam_result_summary,
)
from .analysis.scores import get_score_summary
from .analysis.trends import get_trend_data
from .analysis.classroom import get_classroom_summary
from .analysis.preference import get_preference_summary

logger = logging.getLogger("goukaku_analytics")

app = FastAPI(title="合格実績分析ダッシュボード")


# ─── ポータル統合 ─────────────────────────────────────────


@app.middleware("http")
async def portal_auth(request: Request, call_next):
    """BEHIND_PORTAL=true 時、X-Portal-Role ヘッダーがあれば認証スキップ"""
    if os.environ.get("BEHIND_PORTAL") == "true" and request.headers.get("X-Portal-Role"):
        return await call_next(request)
    return await call_next(request)


def _base_href(request: Request) -> str:
    """ポータル経由の場合は X-Portal-Prefix からベースパスを返す。スタンドアロンは /"""
    prefix = request.headers.get("X-Portal-Prefix", "")
    return f"{prefix}/" if prefix else "/"


TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.globals["enumerate"] = enumerate
templates.env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False, default=json_default)


# ─── グローバル例外ハンドラー ─────────────────────────────


def _error_response(request: Request, message: str, status_code: int = 500):
    """エラー時に dashboard.html でメッセージを表示"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "no_data": True,
         "upload_error": message, "active": "dashboard",
         "base_href": _base_href(request)},
        status_code=status_code,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP %s: %s %s", exc.status_code, request.method, request.url.path)
    return _error_response(
        request,
        f"エラー {exc.status_code}: {exc.detail or 'ページが見つかりません'}",
        exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return _error_response(request, "サーバー内部エラーが発生しました。ログを確認してください。")


# ─── アップロードファイル管理 ─────────────────────────────

_UPLOAD_DIR = Path(tempfile.gettempdir()) / "goukaku_analytics"
_current_upload: dict = {"path": None, "filename": None}
_ALLOWED_UPLOAD_EXTS = {".xlsx", ".xlsm", ".xltx", ".xltm"}


def _safe_upload_name(raw_name: str | None) -> str:
    name = Path(raw_name or "upload.xlsx").name
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)


def _get_current_excel() -> tuple[Path, int] | tuple[None, None]:
    """現在有効な Excel ファイルのパスと年度を返す"""
    if _current_upload["path"]:
        path = Path(_current_upload["path"])
        if path.exists():
            m = re.search(r"20\d{2}", _current_upload["filename"] or "")
            year = int(m.group()) if m else 2026
            return path, year

    year_paths = settings.get_year_paths()
    if not year_paths:
        return None, None
    latest_year = max(year_paths.keys())
    return year_paths[latest_year], latest_year


def _current_filename() -> str | None:
    if _current_upload["filename"]:
        return _current_upload["filename"]
    year_paths = settings.get_year_paths()
    if year_paths:
        return year_paths[max(year_paths.keys())].name
    return None


templates.env.globals["current_filename"] = _current_filename


# ─── アップロード API ─────────────────────────────────────


@app.post("/upload/clear")
async def clear_upload(request: Request):
    _current_upload["path"] = None
    _current_upload["filename"] = None

    project_root = Path(__file__).parent.parent.parent
    for xlsx in list(project_root.glob("EntranceExam_Results_*.xlsx")):
        try:
            xlsx.unlink()
        except Exception:
            pass

    return RedirectResponse(_base_href(request), status_code=303)


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    safe_name = _safe_upload_name(file.filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_EXTS:
        return JSONResponse(
            {"ok": False, "error": "未対応の形式です。.xlsx / .xlsm のみ対応しています。"},
            status_code=400,
        )

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = _UPLOAD_DIR / safe_name

    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

        if not dest.exists() or dest.stat().st_size == 0:
            raise ValueError("empty upload")

        _current_upload["path"] = dest
        _current_upload["filename"] = safe_name
        return JSONResponse({"ok": True})
    except Exception:
        if dest.exists():
            try:
                dest.unlink()
            except Exception:
                pass
        return JSONResponse(
            {"ok": False, "error": "ファイルの保存に失敗しました。"},
            status_code=500,
        )
    finally:
        await file.close()


# ─── ページルート ─────────────────────────────────────────


def _parse_filters(request: Request) -> dict:
    """クエリパラメータからフィルタ条件を取得"""
    return {
        "classroom": request.query_params.get("classroom", ""),
        "school": request.query_params.get("school", ""),
        "bunri": request.query_params.get("bunri", ""),
        "kokushi": request.query_params.get("kokushi", ""),
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    base_href = _base_href(request)
    path, year = _get_current_excel()
    if path is None:
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "no_data": True, "active": "dashboard",
             "base_href": base_href},
        )
    try:
        df_full = load_data(path)
        filters = _parse_filters(request)
        df = apply_filters(df_full, filters)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "year": year,
                "update_date": get_update_date(df_full),
                "summary": get_pass_summary(df),
                "method_by_kokushi": get_method_by_kokushi(df),
                "exam_result": get_exam_result_summary(df),
                "filter_options": get_filter_options(df_full),
                "filters": filters,
                "active": "dashboard",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Dashboard load error: %s", e, exc_info=True)
        return _error_response(request, "ファイルを解析できませんでした。正しいExcelファイルか確認してください。")


@app.get("/summary", response_class=HTMLResponse)
async def summary_page(request: Request):
    base_href = _base_href(request)
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse(base_href, status_code=302)
    try:
        df_full = load_data(path)
        filters = _parse_filters(request)
        df = apply_filters(df_full, filters)
        return templates.TemplateResponse(
            "summary.html",
            {
                "request": request,
                "year": year,
                "summary": get_pass_summary(df),
                "ranking": get_university_ranking(df),
                "method": get_method_summary(df),
                "filter_options": get_filter_options(df_full),
                "filters": filters,
                "active": "summary",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Summary load error: %s", e, exc_info=True)
        return _error_response(request, "集計データの読み込みに失敗しました。ファイルを確認してください。")


@app.get("/scores", response_class=HTMLResponse)
async def scores_page(request: Request):
    base_href = _base_href(request)
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse(base_href, status_code=302)
    try:
        df_full = load_data(path)
        filters = _parse_filters(request)
        df = apply_filters(df_full, filters)
        scores = get_score_summary(df)
        return templates.TemplateResponse(
            "scores.html",
            {
                "request": request,
                "year": year,
                "scores": scores,
                "scores_json": json.dumps(scores, ensure_ascii=False, default=json_default),
                "filter_options": get_filter_options(df_full),
                "filters": filters,
                "active": "scores",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Scores load error: %s", e, exc_info=True)
        return _error_response(request, "得点データの読み込みに失敗しました。ファイルを確認してください。")


@app.get("/classroom", response_class=HTMLResponse)
async def classroom_page(request: Request):
    base_href = _base_href(request)
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse(base_href, status_code=302)
    try:
        df_full = load_data(path)
        filters = _parse_filters(request)
        df = apply_filters(df_full, filters)
        return templates.TemplateResponse(
            "classroom.html",
            {
                "request": request,
                "year": year,
                "classroom": get_classroom_summary(df),
                "filter_options": get_filter_options(df_full),
                "filters": filters,
                "active": "classroom",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Classroom load error: %s", e, exc_info=True)
        return _error_response(request, "教室別データの読み込みに失敗しました。")


@app.get("/preference", response_class=HTMLResponse)
async def preference_page(request: Request):
    base_href = _base_href(request)
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse(base_href, status_code=302)
    try:
        df_full = load_data(path)
        filters = _parse_filters(request)
        df = apply_filters(df_full, filters)
        return templates.TemplateResponse(
            "preference.html",
            {
                "request": request,
                "year": year,
                "pref": get_preference_summary(df),
                "filter_options": get_filter_options(df_full),
                "filters": filters,
                "active": "preference",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Preference load error: %s", e, exc_info=True)
        return _error_response(request, "志望順位データの読み込みに失敗しました。")


@app.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request):
    base_href = _base_href(request)
    year_paths = settings.get_year_paths()
    if not year_paths:
        return RedirectResponse(base_href, status_code=302)
    try:
        year_dfs = load_all_years(year_paths)
        trend = get_trend_data(year_dfs)
        return templates.TemplateResponse(
            "trends.html",
            {
                "request": request,
                "trend": trend,
                "trend_json": json.dumps(trend["chart"], ensure_ascii=False, default=json_default),
                "active": "trends",
                "base_href": base_href,
            },
        )
    except Exception as e:
        logger.error("Trends load error: %s", e, exc_info=True)
        return _error_response(request, "経年比較データの読み込みに失敗しました。")


# ─── htmx 部分更新エンドポイント ──────────────────────────


@app.get("/partials/summary-table", response_class=HTMLResponse)
async def partial_summary_table(request: Request):
    path, _ = _get_current_excel()
    if path is None:
        return HTMLResponse("")
    df = load_data(path)
    return templates.TemplateResponse(
        "partials/summary_table.html",
        {"request": request, "summary": get_pass_summary(df)},
    )


@app.get("/partials/ranking", response_class=HTMLResponse)
async def partial_ranking(request: Request):
    path, _ = _get_current_excel()
    if path is None:
        return HTMLResponse("")
    df = load_data(path)
    return templates.TemplateResponse(
        "partials/ranking_table.html",
        {"request": request, "ranking": get_university_ranking(df)},
    )
