from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
import re
import tempfile

from .config import settings
from .loader import load_data, get_update_date, load_all_years
from .analysis.summary import get_pass_summary, get_university_ranking, get_method_summary
from .analysis.scores import get_score_summary
from .analysis.trends import get_trend_data

app = FastAPI(title="合格実績分析ダッシュボード")

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.globals["enumerate"] = enumerate
templates.env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)

# アップロードファイルの一時保存
_UPLOAD_DIR = Path(tempfile.gettempdir()) / "goukaku_analytics"
_current_upload: dict = {"path": None, "filename": None}


def _get_current_excel() -> tuple[Path, int] | tuple[None, None]:
    if _current_upload["path"] and Path(str(_current_upload["path"])).exists():
        path = Path(str(_current_upload["path"]))
        m = re.search(r"20\d{2}", _current_upload["filename"] or "")
        year = int(m.group()) if m else _default_year()
        return path, year
    year_paths = settings.get_year_paths()
    if not year_paths:
        return None, None
    latest_year = max(year_paths.keys())
    return year_paths[latest_year], latest_year




def _default_year() -> int:
    year_paths = settings.get_year_paths()
    return max(year_paths.keys()) if year_paths else 2026


def _current_filename() -> str | None:
    if _current_upload["filename"]:
        return _current_upload["filename"]
    year_paths = settings.get_year_paths()
    if year_paths:
        return year_paths[max(year_paths.keys())].name
    return None


templates.env.globals["current_filename"] = _current_filename


@app.post("/upload/clear")
async def clear_upload():
    _current_upload["path"] = None
    _current_upload["filename"] = None
    return RedirectResponse("/", status_code=303)


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    from fastapi.responses import JSONResponse
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = _UPLOAD_DIR / (file.filename or "upload.xlsx")
    contents = await file.read()
    dest.write_bytes(contents)
    _current_upload["path"] = dest
    _current_upload["filename"] = file.filename
    return JSONResponse({"ok": True})


# ─── ページルート ────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    path, year = _get_current_excel()
    if path is None:
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "no_data": True, "active": "dashboard"},
        )
    df = load_data(path)
    update_date = get_update_date(path)
    summary = get_pass_summary(df)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "year": year,
            "update_date": update_date,
            "excel_path": str(path),
            "summary": summary,
            "active": "dashboard",
        },
    )


@app.get("/summary", response_class=HTMLResponse)
async def summary_page(request: Request):
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse("/", status_code=302)
    df = load_data(path)
    summary = get_pass_summary(df)
    ranking = get_university_ranking(df)
    method = get_method_summary(df)

    return templates.TemplateResponse(
        "summary.html",
        {
            "request": request,
            "year": year,
            "summary": summary,
            "ranking": ranking,
            "method": method,
            "active": "summary",
        },
    )


@app.get("/scores", response_class=HTMLResponse)
async def scores_page(request: Request):
    path, year = _get_current_excel()
    if path is None:
        return RedirectResponse("/", status_code=302)
    df = load_data(path)
    scores = get_score_summary(df)

    return templates.TemplateResponse(
        "scores.html",
        {
            "request": request,
            "year": year,
            "scores": scores,
            "scores_json": json.dumps(scores, ensure_ascii=False),
            "active": "scores",
        },
    )


@app.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request):
    year_paths = settings.get_year_paths()
    if not year_paths:
        return RedirectResponse("/", status_code=302)

    year_dfs = load_all_years(year_paths)
    trend = get_trend_data(year_dfs)

    return templates.TemplateResponse(
        "trends.html",
        {
            "request": request,
            "trend": trend,
            "trend_json": json.dumps(trend["chart"], ensure_ascii=False),
            "active": "trends",
        },
    )


# ─── htmx 部分更新エンドポイント ────────────────────────


@app.get("/partials/summary-table", response_class=HTMLResponse)
async def partial_summary_table(request: Request):
    path, year = _get_current_excel()
    df = load_data(path)
    summary = get_pass_summary(df)
    return templates.TemplateResponse(
        "partials/summary_table.html",
        {"request": request, "summary": summary},
    )


@app.get("/partials/ranking", response_class=HTMLResponse)
async def partial_ranking(request: Request):
    path, year = _get_current_excel()
    df = load_data(path)
    ranking = get_university_ranking(df)
    return templates.TemplateResponse(
        "partials/ranking_table.html",
        {"request": request, "ranking": ranking},
    )
