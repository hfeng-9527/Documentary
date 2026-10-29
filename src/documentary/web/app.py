"""网页（FastAPI + Jinja2 + htmx）。迭代 0 只有首页和健康检查。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from documentary import __version__
from documentary.core.config import Settings, check_config, load_settings
from documentary.core.db import db_status, make_engine, recent_runs

HERE = Path(__file__).parent

STATUS_ZH = {"running": "运行中", "success": "成功", "partial": "部分失败", "failed": "失败"}
TRIGGER_ZH = {"cli": "命令行", "cron": "定时", "web": "网页按钮"}


def _localtime(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:  # SQLite 不存时区，存进去的都是 UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="纪录片跟踪", version=__version__, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["localtime"] = _localtime
    templates.env.globals.update(version=__version__, STATUS_ZH=STATUS_ZH, TRIGGER_ZH=TRIGGER_ZH)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        check = check_config(settings.config_dir)
        db = db_status(settings)
        runs = []
        if db.up_to_date:
            engine = make_engine(settings)
            try:
                runs = recent_runs(engine)
            finally:
                engine.dispose()
        return templates.TemplateResponse(
            request, "index.html", {"check": check, "db": db, "runs": runs, "settings": settings}
        )

    @app.get("/health", response_class=PlainTextResponse)
    def health():
        return "ok"

    return app
