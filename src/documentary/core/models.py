"""数据表（data-model.md）。按迭代逐步建表（data-model.md 第 5 节）。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Run(Base):
    """运行记录：每次任务一行（data-model.md「run 运行记录」）。排队、进度字段在迭代 3 加。"""

    __tablename__ = "run"

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String(40))
    trigger: Mapped[str] = mapped_column(String(10))  # cli / cron / web
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10))  # running / success / partial / failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    report_path: Mapped[str | None] = mapped_column(String(300))


# ---------- 迭代 1：清单、作品、季、集、编号、主题、评分、状态 ----------
#
# 状态在库里存英文代码，网页显示中文（web/app.py 的 *_ZH）：
#   跟踪状态 tracking_status：pending 待审核 / included 已收录 / excluded 已排除 /
#                             watching 观察中 / upcoming 待播
#   片源状态 library_status： missing 未入库 / planned 计划中 / have 已入库


class Brand(Base):
    """品牌（config/brands.yaml，每次运行时同步）。"""

    __tablename__ = "brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    start_year: Mapped[int] = mapped_column(Integer)
    tmdb_networks: Mapped[list[int]] = mapped_column(JSON, default=list)
    tmdb_companies: Mapped[list[int]] = mapped_column(JSON, default=list)
    default_themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SeriesWatch(Base):
    """重点栏目（config/series.yaml，每次运行时同步）。"""

    __tablename__ = "series_watch"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    tmdb_tv_id: Mapped[int | None] = mapped_column(Integer)
    brand_code: Mapped[str | None] = mapped_column(String(20))
    themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    per_episode: Mapped[bool] = mapped_column(Boolean, default=False)
    since_year: Mapped[int] = mapped_column(Integer, default=2010)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Theme(Base):
    """主题（config/themes.yaml，每次运行时同步）。大类的 parent_key 为空。"""

    __tablename__ = "theme"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    parent_key: Mapped[str | None] = mapped_column(String(60))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Title(Base):
    """作品：系列 / 长片 / YouTube 视频（data-model.md 第 2.2 节）。"""

    __tablename__ = "title"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # series / film / video
    title_en: Mapped[str | None] = mapped_column(String(500))
    title_zh: Mapped[str | None] = mapped_column(String(500))
    title_original: Mapped[str | None] = mapped_column(String(500))
    original_language: Mapped[str | None] = mapped_column(String(10))
    year: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[date | None] = mapped_column(Date)
    overview_en: Mapped[str | None] = mapped_column(Text)
    overview_zh: Mapped[str | None] = mapped_column(Text)
    runtime_min: Mapped[int | None] = mapped_column(Integer)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brand.id"))
    series_watch_id: Mapped[int | None] = mapped_column(ForeignKey("series_watch.id"))
    producers: Mapped[list[str]] = mapped_column(JSON, default=list)
    discovered_via: Mapped[str] = mapped_column(String(20))  # brand / series_watch / …
    tracking_status: Mapped[str] = mapped_column(String(10))
    tracking_reason: Mapped[str | None] = mapped_column(Text)
    screen_suggestion: Mapped[str | None] = mapped_column(String(10))  # include / exclude
    screen_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    upcoming_date: Mapped[date | None] = mapped_column(Date)
    watch_until: Mapped[date | None] = mapped_column(Date)
    library_status: Mapped[str | None] = mapped_column(String(10))  # 只对长片、视频
    poster_path: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    brand: Mapped[Brand | None] = relationship()
    series_watch: Mapped[SeriesWatch | None] = relationship()
    seasons: Mapped[list[Season]] = relationship(
        back_populates="title", order_by="Season.season_number", cascade="all, delete-orphan"
    )
    themes: Mapped[list[TitleTheme]] = relationship(
        back_populates="title", cascade="all, delete-orphan"
    )

    @property
    def per_episode(self) -> bool:
        return bool(self.series_watch and self.series_watch.per_episode)

    @property
    def display_title(self) -> str:
        return self.title_zh or self.title_en or self.title_original or f"#{self.id}"


class Season(Base):
    __tablename__ = "season"
    __table_args__ = (UniqueConstraint("title_id", "season_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id", ondelete="CASCADE"), index=True)
    season_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(300))
    air_date: Mapped[date | None] = mapped_column(Date)
    episode_count: Mapped[int | None] = mapped_column(Integer)
    library_status: Mapped[str | None] = mapped_column(String(10))  # 普通系列在这里记

    title: Mapped[Title] = relationship(back_populates="seasons")
    episodes: Mapped[list[Episode]] = relationship(
        back_populates="season", order_by="Episode.episode_number", cascade="all, delete-orphan"
    )


class Episode(Base):
    __tablename__ = "episode"
    __table_args__ = (UniqueConstraint("season_id", "episode_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"), index=True)
    episode_number: Mapped[int] = mapped_column(Integer)
    name_en: Mapped[str | None] = mapped_column(String(500))
    name_zh: Mapped[str | None] = mapped_column(String(500))
    air_date: Mapped[date | None] = mapped_column(Date)
    runtime_min: Mapped[int | None] = mapped_column(Integer)
    overview: Mapped[str | None] = mapped_column(Text)
    library_status: Mapped[str | None] = mapped_column(String(10))  # 长青栏目在这里记

    season: Mapped[Season] = relationship(back_populates="episodes")


class ExternalRef(Base):
    """各来源编号。TMDB 编号带类别：tv/1966、movie/603、season/…、episode/…"""

    __tablename__ = "external_ref"
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        Index("ix_external_ref_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(10))  # title / season / episode
    entity_id: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10))  # tmdb / imdb / douban / youtube / jellyfin
    external_id: Mapped[str] = mapped_column(String(60))
    match_method: Mapped[str] = mapped_column(String(10), default="source")  # source/id/manual


class TitleTheme(Base):
    __tablename__ = "title_theme"
    __table_args__ = (UniqueConstraint("title_id", "theme_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("title.id", ondelete="CASCADE"), index=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("theme.id"))
    # preset 栏目预设 / default 品牌默认 / source 来源分类 / keyword 关键词 / llm / manual 人工
    origin: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float | None] = mapped_column(Float)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    title: Mapped[Title] = relationship(back_populates="themes")
    theme: Mapped[Theme] = relationship()


class Rating(Base):
    """评分记录：分数或人数变了才新增一行，没变只更新 confirmed_at。"""

    __tablename__ = "rating"
    __table_args__ = (Index("ix_rating_entity", "entity_type", "entity_id", "source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(10))
    entity_id: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10))  # imdb / douban / tmdb
    score: Mapped[float | None] = mapped_column(Float)
    votes: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin: Mapped[str] = mapped_column(String(10), default="auto")  # auto / manual


class StatusEvent(Base):
    """状态变化记录（跟踪状态、片源状态）。"""

    __tablename__ = "status_event"
    __table_args__ = (Index("ix_status_event_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(10))
    entity_id: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(10))  # tracking / library
    old_value: Mapped[str | None] = mapped_column(String(10))
    new_value: Mapped[str | None] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(10))  # system / manual / jellyfin
    run_id: Mapped[int | None] = mapped_column(ForeignKey("run.id"))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceCheckpoint(Base):
    """各来源、各品牌/栏目的检查进度。"""

    __tablename__ = "source_checkpoint"
    __table_args__ = (UniqueConstraint("source", "scope_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(10))
    scope_key: Mapped[str] = mapped_column(String(80))  # brand:UK-2 / series:nova
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    backfill_cursor: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
