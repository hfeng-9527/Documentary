"""网页用的查询：列表筛选、排序、搜索、统计。网页只读写数据库，不调外部接口。

作品数量是几千条的量级，筛选条件用 SQL，片源汇总和评分排序查出来后在 Python 里做，足够快。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from documentary.core.models import Brand, Rating, StatusEvent, Theme, Title, TitleTheme
from documentary.pipeline.states import (
    HAVE,
    INCLUDED,
    PENDING,
    UPCOMING,
    LibrarySummary,
    library_summaries,
)

PAGE_SIZE = 50
SORTS = {"rating": "TMDB 评分", "year": "年份（新的在前）", "title": "标题"}
KINDS = {"series": "系列", "film": "长片", "video": "YouTube"}
LIBRARY_FILTERS = {
    "missing": "未入库",
    "planned": "有计划中",
    "partial": "部分入库",
    "have": "全部已入库",
}


@dataclass
class Filters:
    brand: str = ""
    theme: str = ""
    kind: str = ""
    year_from: int | None = None
    year_to: int | None = None
    library: str = ""
    status: str = INCLUDED
    sort: str = "rating"
    page: int = 1

    def query_string(self, **override) -> str:
        from urllib.parse import urlencode

        d = {**self.__dict__, **override}
        return urlencode({k: v for k, v in d.items() if v not in (None, "")})


@dataclass
class Row:
    title: Title
    library: LibrarySummary
    rating: tuple[float | None, int | None] | None = None
    themes: list[str] = field(default_factory=list)


@dataclass
class Page:
    rows: list[Row]
    total: int
    page: int
    pages: int


def list_titles(s: Session, f: Filters, *, to_download: bool = False) -> Page:
    q = select(Title).options(
        selectinload(Title.series_watch),
        selectinload(Title.brand),
        selectinload(Title.themes).selectinload(TitleTheme.theme),
    )
    q = q.where(Title.tracking_status == (INCLUDED if to_download else f.status or INCLUDED))
    if f.brand:
        q = q.join(Brand, Title.brand_id == Brand.id).where(Brand.code == f.brand)
    if f.kind:
        q = q.where(Title.kind == f.kind)
    if f.year_from:
        q = q.where(Title.year >= f.year_from)
    if f.year_to:
        q = q.where(Title.year <= f.year_to)
    if f.theme:
        sub = (
            select(TitleTheme.title_id)
            .join(Theme, TitleTheme.theme_id == Theme.id)
            .where(or_(Theme.key == f.theme, Theme.key.like(f.theme + ".%")))
        )
        q = q.where(Title.id.in_(sub))
    titles = list(s.scalars(q))

    lib = library_summaries(s, titles)
    rows = [Row(t, lib[t.id]) for t in titles]
    if to_download:  # 待下载：还没全部入库的
        rows = [r for r in rows if r.library.status not in (HAVE, "none")]
    if f.library:
        rows = [r for r in rows if _match_library(r.library, f.library)]

    ratings = latest_ratings(s, [r.title.id for r in rows])
    for r in rows:
        r.rating = ratings.get(r.title.id)
    if f.sort == "year":
        rows.sort(key=lambda r: (r.title.year or 0, r.title.id), reverse=True)
    elif f.sort == "title":
        rows.sort(key=lambda r: r.title.display_title.lower())
    else:
        rows.sort(key=lambda r: ((r.rating or (None,))[0] or 0, r.title.year or 0), reverse=True)

    total = len(rows)
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(max(1, f.page), pages)
    return Page(rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE], total, page, pages)


def _match_library(lib: LibrarySummary, want: str) -> bool:
    if want == "planned":
        return lib.planned > 0
    if want == "missing":
        return lib.have == 0 and lib.planned == 0 and lib.total > 0
    return lib.status == want


def latest_ratings(
    s: Session, title_ids: list[int], source: str = "tmdb"
) -> dict[int, tuple[float | None, int | None]]:
    if not title_ids:
        return {}
    last = (
        select(func.max(Rating.id))
        .where(
            Rating.entity_type == "title",
            Rating.source == source,
            Rating.entity_id.in_(title_ids),
        )
        .group_by(Rating.entity_id)
    )
    rows = s.execute(
        select(Rating.entity_id, Rating.score, Rating.votes).where(Rating.id.in_(last))
    )
    return {tid: (score, votes) for tid, score, votes in rows}


def ratings_for(s: Session, title: Title) -> list[Rating]:
    """详情页：各来源最新一次评分。"""
    last = (
        select(func.max(Rating.id))
        .where(Rating.entity_type == "title", Rating.entity_id == title.id)
        .group_by(Rating.source)
    )
    return list(s.scalars(select(Rating).where(Rating.id.in_(last)).order_by(Rating.source)))


def search(s: Session, q: str, limit: int = 100) -> list[Title]:
    q = q.strip()
    if not q:
        return []
    if (
        len(q) >= 3
    ):  # 三个字及以上用全文检索（trigram），一两个字用模糊匹配（data-model.md 第 4 节）
        ids = s.execute(
            text("SELECT rowid FROM title_fts WHERE title_fts MATCH :q LIMIT :n"),
            {"q": '"' + q.replace('"', '""') + '"', "n": limit},
        ).scalars()
        cond = Title.id.in_(list(ids))
    else:
        like = f"%{q}%"
        cond = or_(
            Title.title_en.ilike(like), Title.title_zh.like(like), Title.title_original.ilike(like)
        )
    rows = s.scalars(
        select(Title).options(selectinload(Title.brand)).where(cond).limit(limit)
    ).all()
    order = {INCLUDED: 0, PENDING: 1, UPCOMING: 2}
    return sorted(rows, key=lambda t: (order.get(t.tracking_status, 3), -(t.year or 0)))


def review_groups(s: Session) -> list[tuple[Brand | None, list[Title]]]:
    """待审核条目按品牌分组。"""
    titles = s.scalars(
        select(Title)
        .options(
            selectinload(Title.brand), selectinload(Title.themes).selectinload(TitleTheme.theme)
        )
        .where(Title.tracking_status == PENDING)
        .order_by(Title.year.desc(), Title.id)
    ).all()
    groups: dict[int | None, list[Title]] = {}
    for t in titles:
        groups.setdefault(t.brand_id, []).append(t)
    brands = {b.id: b for b in s.scalars(select(Brand))}
    out = [(brands.get(bid), items) for bid, items in groups.items()]
    return sorted(out, key=lambda g: (g[0] is None, g[0].code if g[0] else ""))


def counts(s: Session) -> dict[str, int]:
    by_status = dict(
        s.execute(select(Title.tracking_status, func.count()).group_by(Title.tracking_status)).all()
    )
    included = list(s.scalars(select(Title).where(Title.tracking_status == INCLUDED)))
    lib = library_summaries(s, included)
    return {
        **by_status,
        "planned_titles": sum(1 for v in lib.values() if v.planned),
        "have_titles": sum(1 for v in lib.values() if v.status == HAVE),
    }


def history(s: Session, title: Title) -> list[StatusEvent]:
    return list(
        s.scalars(
            select(StatusEvent)
            .where(
                StatusEvent.entity_type == "title",
                StatusEvent.entity_id == title.id,
                StatusEvent.field == "tracking",
            )
            .order_by(StatusEvent.id.desc())
        )
    )


def all_themes(s: Session) -> list[Theme]:
    return list(s.scalars(select(Theme).order_by(Theme.sort)))


def all_brands(s: Session) -> list[Brand]:
    return list(s.scalars(select(Brand).order_by(Brand.code)))
