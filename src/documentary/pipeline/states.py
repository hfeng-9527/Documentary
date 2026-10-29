"""两个状态的流转和记录（data-model.md 第 3 节、scenarios.md 第 2 节）。

每次状态变化都写一条 status_event：改了什么、谁改的、为什么、哪次任务。
片源状态：普通系列记在季上，长青栏目记在集上，长片和视频记在作品上；
作品建立时就给季/集设成“未入库”，网页只对“已收录”的作品显示。
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from documentary.core.models import Episode, Season, StatusEvent, Title

PENDING, INCLUDED, EXCLUDED, WATCHING, UPCOMING = (
    "pending",
    "included",
    "excluded",
    "watching",
    "upcoming",
)
TRACKING_ZH = {
    PENDING: "待审核",
    INCLUDED: "已收录",
    EXCLUDED: "已排除",
    WATCHING: "观察中",
    UPCOMING: "待播",
}
MISSING, PLANNED, HAVE = "missing", "planned", "have"
LIBRARY_ZH = {MISSING: "未入库", PLANNED: "计划中", HAVE: "已入库"}
ACTOR_ZH = {"system": "系统", "manual": "人工", "jellyfin": "Jellyfin 同步"}

Entity = Title | Season | Episode


def entity_type(obj: Entity) -> str:
    return {Title: "title", Season: "season", Episode: "episode"}[type(obj)]


def set_tracking(
    s: Session,
    title: Title,
    new: str,
    *,
    reason: str | None,
    actor: str,
    run_id: int | None = None,
) -> bool:
    if new not in TRACKING_ZH:
        raise ValueError(f"未知的跟踪状态：{new}")
    old = title.tracking_status or None  # 新建的作品还没有状态
    if old == new:
        return False
    title.tracking_status = new
    title.tracking_reason = reason
    s.flush()  # 新建的作品要先有 id
    s.add(
        StatusEvent(
            entity_type="title",
            entity_id=title.id,
            field="tracking",
            old_value=old,
            new_value=new,
            reason=reason,
            actor=actor,
            run_id=run_id,
        )
    )
    return True


def set_library(
    s: Session,
    obj: Entity,
    new: str,
    *,
    actor: str,
    reason: str | None = None,
    run_id: int | None = None,
) -> bool:
    if new not in LIBRARY_ZH:
        raise ValueError(f"未知的片源状态：{new}")
    old = obj.library_status
    if old == new:
        return False
    obj.library_status = new
    s.flush()
    s.add(
        StatusEvent(
            entity_type=entity_type(obj),
            entity_id=obj.id,
            field="library",
            old_value=old,
            new_value=new,
            reason=reason,
            actor=actor,
            run_id=run_id,
        )
    )
    return True


@dataclass
class LibrarySummary:
    unit: str  # 季 / 集 / ""（长片、视频）
    total: int
    have: int
    planned: int

    @property
    def status(self) -> str:
        """作品整体：have 全部入库 / partial 部分 / planned 有计划中 / missing / none（没有季集）"""
        if self.total == 0:
            return "none"
        if self.have == self.total:
            return HAVE
        if self.have:
            return "partial"
        return PLANNED if self.planned else MISSING

    @property
    def text(self) -> str:
        if self.unit == "":
            return LIBRARY_ZH.get(self.status, "")
        if self.total == 0:
            return f"没有{self.unit}"
        if self.unit == "集":
            parts = [f"已入库 {self.have} 集"] if self.have else []
            if self.planned:
                parts.append(f"计划中 {self.planned} 集")
            return "，".join(parts) or f"未入库（共 {self.total} 集）"
        if self.have == self.total:
            return f"全部已入库（{self.total} 季）"
        text = f"{self.have}/{self.total} 季已入库" if self.have else "未入库"
        return text + (f"，计划中 {self.planned} 季" if self.planned else "")


def library_summaries(s: Session, titles: list[Title]) -> dict[int, LibrarySummary]:
    """一次查出多部作品的片源汇总（列表页用，避免逐部加载几百集）。"""
    out: dict[int, LibrarySummary] = {}
    per_ep = [t.id for t in titles if t.kind == "series" and t.per_episode]
    per_season = [t.id for t in titles if t.kind == "series" and not t.per_episode]

    def counts(model, ids):
        status = model.library_status
        q = select(
            Season.title_id,
            func.count(),
            func.sum(case((status == HAVE, 1), else_=0)),
            func.sum(case((status == PLANNED, 1), else_=0)),
        ).select_from(model)
        if model is Episode:
            q = q.join(Season, Episode.season_id == Season.id)
        return s.execute(q.where(Season.title_id.in_(ids)).group_by(Season.title_id)).all()

    if per_season:
        for tid, total, have, planned in counts(Season, per_season):
            out[tid] = LibrarySummary("季", total, have or 0, planned or 0)
    if per_ep:
        for tid, total, have, planned in counts(Episode, per_ep):
            out[tid] = LibrarySummary("集", total, have or 0, planned or 0)
    for t in titles:
        if t.id in out:
            continue
        if t.kind == "series":
            out[t.id] = LibrarySummary("集" if t.per_episode else "季", 0, 0, 0)
        else:
            st = t.library_status or MISSING
            out[t.id] = LibrarySummary("", 1, int(st == HAVE), int(st == PLANNED))
    return out
