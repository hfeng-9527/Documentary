"""把 config/*.yaml 里的清单（品牌、重点栏目、主题）同步进数据库。

配置文件是清单的唯一来源（data-model.md 第 1.1 节）：每次运行时同步，网页上不改清单。
配置里删掉的条目不删数据库记录（作品还引用着它），只标成不收录。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from documentary.core.config import Catalog
from documentary.core.models import Brand, SeriesWatch, Theme


def sync_catalog(s: Session, catalog: Catalog) -> None:
    brands = {b.code: b for b in s.scalars(select(Brand))}
    for b in catalog.brands:
        row = brands.pop(b.code, None) or Brand(code=b.code)
        row.name, row.start_year, row.notes, row.enabled = b.name, b.start_year, b.notes, b.enabled
        row.tmdb_networks, row.tmdb_companies = list(b.tmdb_networks), list(b.tmdb_companies)
        row.default_themes = list(b.default_themes)
        s.add(row)
    for row in brands.values():
        row.enabled = False

    series = {w.key: w for w in s.scalars(select(SeriesWatch))}
    for w in catalog.series:
        row = series.pop(w.key, None) or SeriesWatch(key=w.key)
        row.name, row.tmdb_tv_id, row.brand_code = w.name, w.tmdb_tv_id, w.brand_code
        row.themes, row.per_episode = list(w.themes), w.per_episode
        row.since_year, row.enabled = w.since_year, w.enabled
        s.add(row)
    for row in series.values():
        row.enabled = False

    themes = {t.key: t for t in s.scalars(select(Theme))}
    order = 0
    for t in catalog.themes:
        for key, name, parent in [(t.key, t.name, None)] + [
            (ch.key, ch.name, t.key) for ch in t.children
        ]:
            row = themes.get(key) or Theme(key=key)
            row.name, row.parent_key, row.sort = name, parent, order
            order += 1
            s.add(row)
    s.flush()
