"""网页（FastAPI + Jinja2 + htmx）：首页、审核、作品列表、待下载、详情、搜索。

页面清单见 scenarios.md 第 4 节。

网页只读写数据库，不调外部接口。改状态的按钮用 htmx 局部刷新，不支持 htmx 时退回整页跳转。
"""

# 不用 from __future__ import annotations：FastAPI 要在运行时解析函数里定义的 DB 类型
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from documentary import __version__
from documentary.core.config import Settings, check_config, load_settings
from documentary.core.db import db_status, make_engine, recent_runs
from documentary.core.models import Episode, Run, Season, Title, TitleTheme
from documentary.pipeline import actions
from documentary.pipeline.prescreen import EXCLUDE, INCLUDE, ORIGIN_ZH
from documentary.pipeline.states import (
    ACTOR_ZH,
    INCLUDED,
    LIBRARY_ZH,
    TRACKING_ZH,
    library_summaries,
)
from documentary.web import queries
from documentary.web.queries import Filters

HERE = Path(__file__).parent

STATUS_ZH = {"running": "运行中", "success": "成功", "partial": "部分失败", "failed": "失败"}
TRIGGER_ZH = {"cli": "命令行", "cron": "定时", "web": "网页按钮"}
SUGGESTION_ZH = {INCLUDE: "建议收录", EXCLUDE: "建议排除", None: "需人工判断"}
POSTER_BASE = "https://image.tmdb.org/t/p/w185"


def _localtime(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:  # SQLite 不存时区，存进去的都是 UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone().strftime(fmt)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="纪录片跟踪", version=__version__, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["localtime"] = _localtime
    templates.env.globals.update(
        version=__version__,
        STATUS_ZH=STATUS_ZH,
        TRIGGER_ZH=TRIGGER_ZH,
        TRACKING_ZH=TRACKING_ZH,
        LIBRARY_ZH=LIBRARY_ZH,
        SUGGESTION_ZH=SUGGESTION_ZH,
        ORIGIN_ZH=ORIGIN_ZH,
        ACTOR_ZH=ACTOR_ZH,
        KINDS=queries.KINDS,
        POSTER_BASE=POSTER_BASE,
    )
    engine = make_engine(settings)

    ready = False

    def db() -> Iterator[Session]:
        nonlocal ready
        if not ready:  # 确认过一次是最新的就不再每次检查
            if not db_status(settings).up_to_date:
                raise HTTPException(503, "数据库未初始化或需要升级，先运行 uv run doc db upgrade")
            ready = True
        with Session(engine) as s:
            yield s

    DB = Annotated[Session, Depends(db)]

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        return templates.TemplateResponse(request, name, ctx)

    def back(request: Request, default: str = "/") -> RedirectResponse:
        return RedirectResponse(request.headers.get("referer") or default, status_code=303)

    def is_htmx(request: Request) -> bool:
        return request.headers.get("HX-Request") == "true"

    # ---------- 首页 ----------

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        check = check_config(settings.config_dir)
        dbs = db_status(settings)
        runs, counts, last_discover = [], {}, None
        if dbs.up_to_date:
            runs = recent_runs(engine)
            with Session(engine) as s:
                counts = queries.counts(s)
                last_discover = s.scalar(
                    select(Run).where(Run.task == "discover").order_by(Run.id.desc()).limit(1)
                )
        return render(
            request,
            "index.html",
            check=check,
            db=dbs,
            runs=runs,
            settings=settings,
            counts=counts,
            last_discover=last_discover,
        )

    @app.get("/health", response_class=PlainTextResponse)
    def health():
        return "ok"

    # ---------- 审核 ----------

    @app.get("/review", response_class=HTMLResponse)
    def review(request: Request, s: DB):
        groups = queries.review_groups(s)
        return render(
            request,
            "review.html",
            groups=groups,
            total=sum(len(items) for _brand, items in groups),
            themes=queries.all_themes(s),
        )

    @app.post("/review/{title_id}")
    def review_one(
        request: Request,
        s: DB,
        title_id: int,
        action: Annotated[str, Form()],
        reason: Annotated[str, Form()] = "",
        themes: Annotated[list[str] | None, Form()] = None,
        edit_themes: Annotated[str, Form()] = "",
    ):
        title = _get_title(s, title_id)
        if action == "include":
            actions.include(s, title, themes=(themes or []) if edit_themes else None)
            done = "已收录"
        elif action == "exclude":
            actions.exclude(s, title, reason=reason)
            done = "已排除"
        else:
            raise HTTPException(400, "action 只能是 include 或 exclude")
        s.commit()
        if is_htmx(request):
            return HTMLResponse(
                f'<p class="done muted">{title.display_title}：{done}'
                f' · <a href="/title/{title.id}">详情</a></p>'
            )
        return back(request, "/review")

    @app.post("/review-group")
    def review_group(
        request: Request,
        s: DB,
        mode: Annotated[str, Form()],
        brand_id: Annotated[str, Form()] = "",
    ):
        if mode not in ("all", "suggested"):
            raise HTTPException(400, "mode 只能是 all 或 suggested")
        actions.apply_group(s, int(brand_id) if brand_id else None, mode)
        s.commit()
        return RedirectResponse("/review", status_code=303)

    # ---------- 列表 ----------

    def _filters(
        brand: str = "",
        theme: str = "",
        kind: str = "",
        year_from: Annotated[str, Query()] = "",
        year_to: Annotated[str, Query()] = "",
        library: str = "",
        status: str = INCLUDED,
        sort: str = "rating",
        page: int = 1,
    ) -> Filters:
        return Filters(
            brand=brand,
            theme=theme,
            kind=kind,
            year_from=int(year_from) if year_from.isdigit() else None,
            year_to=int(year_to) if year_to.isdigit() else None,
            library=library,
            status=status if status in TRACKING_ZH else INCLUDED,
            sort=sort if sort in queries.SORTS else "rating",
            page=page,
        )

    def _list(request: Request, s: Session, f: Filters, *, to_download: bool):
        return render(
            request,
            "titles.html",
            page=queries.list_titles(s, f, to_download=to_download),
            f=f,
            to_download=to_download,
            path="/to-download" if to_download else "/titles",
            brands=queries.all_brands(s),
            themes=[t for t in queries.all_themes(s) if t.parent_key is None],
            sorts=queries.SORTS,
            library_filters=queries.LIBRARY_FILTERS,
        )

    @app.get("/titles", response_class=HTMLResponse)
    def titles(request: Request, s: DB, f: Annotated[Filters, Depends(_filters)]):
        return _list(request, s, f, to_download=False)

    @app.get("/to-download", response_class=HTMLResponse)
    def to_download(request: Request, s: DB, f: Annotated[Filters, Depends(_filters)]):
        return _list(request, s, f, to_download=True)

    @app.get("/search", response_class=HTMLResponse)
    def search(request: Request, s: DB, q: str = ""):
        return render(request, "search.html", q=q, results=queries.search(s, q))

    # ---------- 详情 ----------

    @app.get("/title/{title_id}", response_class=HTMLResponse)
    def detail(request: Request, s: DB, title_id: int, open_season: int | None = None):
        title = _get_title(s, title_id)
        return render(
            request,
            "detail.html",
            t=title,
            refs=_refs(s, title),
            ratings=queries.ratings_for(s, title),
            history=queries.history(s, title),
            themes=queries.all_themes(s),
            **_library_ctx(s, title, open_season),
        )

    @app.post("/title/{title_id}/tracking")
    def tracking(
        request: Request,
        s: DB,
        title_id: int,
        status: Annotated[str, Form()],
        reason: Annotated[str, Form()] = "",
    ):
        if status not in TRACKING_ZH:
            raise HTTPException(400, "未知的跟踪状态")
        actions.change_tracking(s, _get_title(s, title_id), status, reason=reason)
        s.commit()
        return RedirectResponse(f"/title/{title_id}", status_code=303)

    @app.post("/title/{title_id}/themes")
    def themes(
        s: DB,
        title_id: int,
        themes: Annotated[list[str] | None, Form()] = None,
    ):
        actions.set_themes(s, _get_title(s, title_id), themes or [])
        s.commit()
        return RedirectResponse(f"/title/{title_id}", status_code=303)

    # ---------- 片源状态 ----------

    def _status(status: str) -> str:
        if status not in LIBRARY_ZH:
            raise HTTPException(400, "片源状态只能是 missing / planned / have")
        return status

    def _library_fragment(request: Request, s: Session, title: Title, open_season: int | None):
        s.commit()
        s.expire_all()
        title = _get_title(s, title.id)
        return render(request, "_library.html", t=title, **_library_ctx(s, title, open_season))

    @app.post("/library/season/{season_id}")
    def library_season(request: Request, s: DB, season_id: int, status: Annotated[str, Form()]):
        se = s.get(Season, season_id) or _404()
        actions.mark(s, se, _status(status))
        if is_htmx(request):
            return _library_fragment(request, s, se.title, None)
        s.commit()
        return back(request)

    @app.post("/library/season/{season_id}/episodes")
    def library_season_episodes(
        request: Request, s: DB, season_id: int, status: Annotated[str, Form()]
    ):
        se = s.get(Season, season_id) or _404()
        actions.mark_season_episodes(s, se, _status(status))
        if is_htmx(request):
            return _library_fragment(request, s, se.title, se.id)
        s.commit()
        return back(request)

    @app.post("/library/episode/{episode_id}")
    def library_episode(request: Request, s: DB, episode_id: int, status: Annotated[str, Form()]):
        ep = s.get(Episode, episode_id) or _404()
        actions.mark(s, ep, _status(status))
        if is_htmx(request):
            return _library_fragment(request, s, ep.season.title, ep.season_id)
        s.commit()
        return back(request)

    @app.post("/library/title/{title_id}")
    def library_title(request: Request, s: DB, title_id: int, status: Annotated[str, Form()]):
        """整部标记（列表页用）：返回这一行的片源单元格。"""
        title = _get_title(s, title_id)
        actions.mark_title(s, title, _status(status))
        s.commit()
        if is_htmx(request):
            s.expire_all()
            title = _get_title(s, title_id)
            lib = library_summaries(s, [title])[title.id]
            return render(request, "_row_library.html", t=title, lib=lib)
        return back(request)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    return app


def _404():
    raise HTTPException(404, "找不到")


def _get_title(s: Session, title_id: int) -> Title:
    title = s.scalar(
        select(Title)
        .options(
            selectinload(Title.brand),
            selectinload(Title.series_watch),
            selectinload(Title.themes).selectinload(TitleTheme.theme),
            selectinload(Title.seasons).selectinload(Season.episodes),
        )
        .where(Title.id == title_id)
    )
    if title is None:
        _404()
    return title


def _refs(s: Session, title: Title) -> dict[str, str]:
    from documentary.core.models import ExternalRef

    rows = s.scalars(
        select(ExternalRef).where(
            ExternalRef.entity_type == "title", ExternalRef.entity_id == title.id
        )
    )
    links = {}
    for r in rows:
        if r.source == "tmdb":
            links["TMDB"] = f"https://www.themoviedb.org/{r.external_id}"
        elif r.source == "imdb":
            links["IMDb"] = f"https://www.imdb.com/title/{r.external_id}/"
    return links


def _library_ctx(s: Session, title: Title, open_season: int | None) -> dict:
    lib = library_summaries(s, [title])[title.id]
    seasons = []
    for se in title.seasons:
        eps = se.episodes
        have = sum(1 for e in eps if e.library_status == "have")
        planned = sum(1 for e in eps if e.library_status == "planned")
        seasons.append({"season": se, "have": have, "planned": planned, "total": len(eps)})
    return {"lib": lib, "seasons": seasons, "open_season": open_season}
