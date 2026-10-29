"""你在网页上的操作：审核（收录 / 排除）、改主题、改跟踪状态、标记片源状态。

所有改动都记成 actor = manual 的状态变化。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from documentary.core.models import Season, Theme, Title, TitleTheme
from documentary.pipeline.prescreen import EXCLUDE, INCLUDE
from documentary.pipeline.states import (
    EXCLUDED,
    INCLUDED,
    PENDING,
    TRACKING_ZH,
    set_library,
    set_tracking,
)

MANUAL = "manual"


def include(s: Session, title: Title, *, themes: list[str] | None = None) -> None:
    if themes is not None:
        set_themes(s, title, themes)
    else:  # 没改主题就是认可现有的
        for tt in title.themes:
            tt.confirmed = True
    set_tracking(s, title, INCLUDED, reason="审核收录", actor=MANUAL)


def exclude(s: Session, title: Title, *, reason: str | None = None) -> None:
    reason = (reason or "").strip() or "审核排除"
    set_tracking(s, title, EXCLUDED, reason=reason, actor=MANUAL)


def change_tracking(s: Session, title: Title, new: str, *, reason: str | None = None) -> None:
    reason = (reason or "").strip() or f"手动改为{TRACKING_ZH.get(new, new)}"
    set_tracking(s, title, new, reason=reason, actor=MANUAL)


def set_themes(s: Session, title: Title, keys: list[str]) -> None:
    """用你选的主题替换现有主题，全部记为人工确认。"""
    themes = {t.key: t for t in s.scalars(select(Theme).where(Theme.key.in_(keys)))}
    keep = set(themes)
    for tt in list(title.themes):
        if tt.theme.key not in keep:
            title.themes.remove(tt)
        else:
            tt.confirmed = True
            keep.discard(tt.theme.key)
    for key in keys:
        if key in keep:
            title.themes.append(TitleTheme(theme_id=themes[key].id, origin=MANUAL, confirmed=True))
            keep.discard(key)


def apply_group(s: Session, brand_id: int | None, mode: str) -> dict[str, int]:
    """整组处理一个品牌的待审核条目。mode：all 全部收录 / suggested 按建议处理。"""
    same_brand = Title.brand_id.is_(None) if brand_id is None else Title.brand_id == brand_id
    titles = s.scalars(select(Title).where(Title.tracking_status == PENDING, same_brand)).all()
    done = {"included": 0, "excluded": 0, "left": 0}
    for t in titles:
        if mode == "all" or t.screen_suggestion == INCLUDE:
            include(s, t)
            done["included"] += 1
        elif t.screen_suggestion == EXCLUDE:
            reason = "按初筛建议排除：" + "；".join(
                r for r in t.screen_reasons if not r.startswith("主题：")
            )
            set_tracking(s, t, EXCLUDED, reason=reason, actor=MANUAL)
            done["excluded"] += 1
        else:
            done["left"] += 1
    return done


def mark(s: Session, obj, status: str) -> None:
    set_library(s, obj, status, actor=MANUAL)


def mark_season_episodes(s: Session, season: Season, status: str) -> None:
    for ep in season.episodes:
        set_library(s, ep, status, actor=MANUAL, reason="整季标记")


def mark_title(s: Session, title: Title, status: str) -> None:
    """整部标记：系列的每一季（长青栏目的每一集），长片和视频就是它本身。"""
    if title.kind != "series":
        set_library(s, title, status, actor=MANUAL)
        return
    for se in title.seasons:
        if title.per_episode:
            for ep in se.episodes:
                set_library(s, ep, status, actor=MANUAL, reason="整部标记")
        else:
            set_library(s, se, status, actor=MANUAL, reason="整部标记")
