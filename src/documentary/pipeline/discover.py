"""发现新内容：`doc discover --source tmdb`（scenarios.md S0；迭代 1 只有 TMDB、只跑试点）。

流程：同步清单 → 逐个重点栏目、品牌抓取 → 初筛 → 写库 → 更新各自的检查时间。
- 重点栏目：每次都重取详情，补上新季、新集，直接“已收录”。
- 品牌：第一次从品牌起始年份全部查一遍，以后只查上次成功之后首播的新系列；
  已经在库里的（包括已排除的）不再重复建、不再进审核。
- 某个品牌失败不影响其他品牌，它的检查时间不前进，下次从它自己的上次成功时间接着查；
  key 错、代理不通这类问题（fatal）直接停止，剩下的不再试。
- dry-run：照常抓取和初筛，最后整体回滚，不写数据库，也不存原始数据。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from documentary.core.config import Catalog, Settings
from documentary.core.http import NotFound, SourceError
from documentary.core.models import (
    Brand,
    Episode,
    ExternalRef,
    Rating,
    Season,
    SeriesWatch,
    SourceCheckpoint,
    Theme,
    Title,
    TitleTheme,
    utcnow,
)
from documentary.core.raw import RawStore
from documentary.pipeline.catalog import sync_catalog
from documentary.pipeline.prescreen import Screening, screen
from documentary.pipeline.states import (
    INCLUDED,
    MISSING,
    PENDING,
    UPCOMING,
    set_tracking,
)
from documentary.sources.tmdb import Tmdb, TmdbSeries

log = logging.getLogger(__name__)

# 迭代 1 只跑试点（pilot: true）；迭代 2a 起改为全部 enabled 的品牌和栏目
PILOT_ONLY = True
# 增量查询往前多查一段，防止 TMDB 晚录入的条目漏掉（重复的会按编号跳过）
OVERLAP = timedelta(days=30)


@dataclass
class NewItem:
    tmdb_id: int
    title: str
    year: int | None
    status: str
    suggestion: str | None
    reasons: list[str]


@dataclass
class TargetResult:
    key: str  # brand:UK-2 / series:nova
    label: str
    since: date | None = None
    found: int = 0
    known: int = 0
    new: list[NewItem] = field(default_factory=list)
    updated: int = 0
    seasons_added: int = 0
    episodes_added: int = 0
    error: str | None = None
    skipped: bool = False  # 前面出了致命错误，没有运行


@dataclass
class DiscoverResult:
    dry_run: bool
    targets: list[TargetResult] = field(default_factory=list)
    requests: int = 0
    fatal: str | None = None

    @property
    def status(self) -> str:
        failed = [t for t in self.targets if t.error or t.skipped]
        if not failed:
            return "success"
        return "failed" if len(failed) == len(self.targets) else "partial"

    def stats(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "requests": self.requests,
            "new": sum(len(t.new) for t in self.targets),
            "targets": {
                t.key: {
                    "found": t.found,
                    "new": len(t.new),
                    "updated": t.updated,
                    "seasons_added": t.seasons_added,
                    "episodes_added": t.episodes_added,
                    "error": t.error,
                    "skipped": t.skipped,
                }
                for t in self.targets
            },
            "fatal": self.fatal,
        }


class TargetNotFound(ValueError):
    pass


def discover_tmdb(
    engine: Engine,
    settings: Settings,
    catalog: Catalog,
    *,
    brand: str | None = None,
    series: str | None = None,
    dry_run: bool = False,
    run_id: int | None = None,
    progress: Callable[[str], None] = lambda _msg: None,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] | None = None,
    today: date | None = None,
) -> DiscoverResult:
    today = today or datetime.now(UTC).date()
    result = DiscoverResult(dry_run=dry_run)
    raw = None if dry_run else RawStore(settings.raw_db_path)
    tmdb = None
    with Session(engine) as s:
        try:
            sync_catalog(s, catalog)
            if not dry_run:
                s.commit()  # 清单先提交，后面某个品牌失败回滚时不会连带撤掉
            targets = _pick_targets(s, catalog, brand, series)
            tmdb = Tmdb(settings, raw, transport=transport, sleep=sleep)
            job = _Job(s, tmdb, catalog, run_id, today, dry_run, progress)
            for target in targets:
                tr = TargetResult(*_target_key(target))
                result.targets.append(tr)
                if result.fatal:
                    tr.skipped = True
                    continue
                progress(f"[{tr.label}] 开始")
                try:
                    if isinstance(target, SeriesWatch):
                        job.run_series(target, tr)
                    else:
                        job.run_brand(target, tr)
                except SourceError as e:
                    tr.error = str(e)
                    job.checkpoint_failed(tr.key, tr.error)
                    if e.fatal:
                        result.fatal = tr.error
                    progress(f"[{tr.label}] 失败：{tr.error}")
                    continue
                job.checkpoint_ok(tr.key)
                progress(
                    f"[{tr.label}] 完成：新增 {len(tr.new)}，更新 {tr.updated}"
                    + (f"，新季 {tr.seasons_added}" if tr.seasons_added else "")
                    + (f"，新集 {tr.episodes_added}" if tr.episodes_added else "")
                )
        finally:
            if tmdb:
                result.requests = tmdb.requests
                tmdb.close()
            if raw:
                raw.close()
            if dry_run:
                s.rollback()
    return result


def _pick_targets(s: Session, catalog: Catalog, brand: str | None, series: str | None) -> list:
    if brand:
        row = s.scalar(select(Brand).where(Brand.code == brand.upper()))
        if not row or not (row.tmdb_networks or row.tmdb_companies):
            raise TargetNotFound(f"brands.yaml 里没有编号为 {brand} 且填了 TMDB 编号的品牌")
        return [row]
    if series:
        row = s.scalar(select(SeriesWatch).where(SeriesWatch.key == series.lower()))
        if not row or row.tmdb_tv_id is None:
            raise TargetNotFound(f"series.yaml 里没有简称为 {series} 且填了 tmdb_tv_id 的栏目")
        return [row]
    sw = s.scalars(
        select(SeriesWatch).where(SeriesWatch.enabled, SeriesWatch.tmdb_tv_id.is_not(None))
    ).all()
    br = s.scalars(select(Brand).where(Brand.enabled)).all()
    br = [b for b in br if b.tmdb_networks or b.tmdb_companies]
    if PILOT_ONLY:  # pilot 标记只在配置里，不进数据库
        sw = [w for w in sw if w.key in {x.key for x in catalog.series if x.pilot}]
        br = [b for b in br if b.code in {x.code for x in catalog.brands if x.pilot}]
    return [*sw, *br]


def _target_key(t) -> tuple[str, str]:
    if isinstance(t, SeriesWatch):
        return f"series:{t.key}", t.name
    return f"brand:{t.code}", f"{t.code} {t.name}"


class _Job:
    def __init__(self, s, tmdb, catalog, run_id, today, dry_run, progress):
        self.s: Session = s
        self.tmdb: Tmdb = tmdb
        self.catalog: Catalog = catalog
        self.rules = catalog.rules
        self.names = catalog.theme_names()
        self.run_id = run_id
        self.today = today
        self.dry_run = dry_run
        self.progress = progress
        self.theme_ids = {t.key: t.id for t in s.scalars(select(Theme))}

    def commit(self) -> None:
        if self.dry_run:
            self.s.flush()
        else:
            self.s.commit()

    # ---------- 检查时间 ----------

    def _checkpoint(self, key: str) -> SourceCheckpoint:
        cp = self.s.scalar(
            select(SourceCheckpoint).where(
                SourceCheckpoint.source == "tmdb", SourceCheckpoint.scope_key == key
            )
        )
        if cp is None:
            cp = SourceCheckpoint(source="tmdb", scope_key=key, consecutive_failures=0)
            self.s.add(cp)
        return cp

    def checkpoint_ok(self, key: str) -> None:
        cp = self._checkpoint(key)
        cp.last_success_at = cp.last_attempt_at = utcnow()
        cp.consecutive_failures, cp.last_error = 0, None
        self.commit()

    def checkpoint_failed(self, key: str, error: str) -> None:
        if self.dry_run:
            return
        self.s.rollback()  # 丢掉这个品牌没提交的半截改动
        cp = self._checkpoint(key)
        cp.last_attempt_at = utcnow()
        cp.consecutive_failures = (cp.consecutive_failures or 0) + 1
        cp.last_error = error
        self.s.commit()

    # ---------- 重点栏目 ----------

    def run_series(self, sw: SeriesWatch, tr: TargetResult) -> None:
        tv = self.tmdb.series(sw.tmdb_tv_id)
        tr.found = 1
        sc = screen(tv, self.rules, self.names, preset=sw.themes)
        title = self._find_title(tv.tmdb_id)
        reason = "重点栏目，直接收录"
        if title is None:
            title = self._create_title(tv, sc, brand=self._brand(sw.brand_code), via="series_watch")
            title.series_watch_id = sw.id
            set_tracking(self.s, title, INCLUDED, reason=reason, actor="system", run_id=self.run_id)
            tr.new.append(self._new_item(title, tv, sc))
        else:
            self._update_title(title, tv, sc)
            title.series_watch_id = sw.id
            if title.tracking_status in (PENDING, UPCOMING):
                set_tracking(
                    self.s, title, INCLUDED, reason=reason, actor="system", run_id=self.run_id
                )
            tr.updated = 1
        self._apply_themes(title, sc)
        self.s.flush()
        self._sync_seasons(title, tv, per_episode=sw.per_episode, since_year=sw.since_year, tr=tr)
        self.commit()

    # ---------- 品牌 ----------

    def run_brand(self, b: Brand, tr: TargetResult) -> None:
        cp = self._checkpoint(tr.key)
        if cp.last_success_at:
            last = cp.last_success_at
            last = last if last.tzinfo else last.replace(tzinfo=UTC)
            since = (last - OVERLAP).date()
        else:
            since = date(b.start_year, 1, 1)
        tr.since = since
        ids: dict[int, None] = {}
        for kind, values in (("networks", b.tmdb_networks), ("companies", b.tmdb_companies)):
            if values:
                for item in self.tmdb.discover_tv(since=since, **{kind: values}):
                    ids.setdefault(int(item["id"]), None)
        tr.found = len(ids)
        self.progress(f"[{tr.label}] {since} 以来找到 {len(ids)} 部，逐部取详情…")
        for n, tv_id in enumerate(ids, start=1):
            if self._find_title(tv_id) is not None:
                tr.known += 1
                continue
            try:
                tv = self.tmdb.series(tv_id)
            except NotFound:
                log.warning("TMDB 剧集 %s 已不存在，跳过", tv_id)
                continue
            sc = screen(tv, self.rules, self.names, brand_default=b.default_themes)
            title = self._create_title(tv, sc, brand=b, via="brand")
            if tv.first_air_date and tv.first_air_date > self.today:
                status, reason = UPCOMING, f"首播日期 {tv.first_air_date}，未播出"
            else:
                status, reason = PENDING, f"按品牌发现（{b.name}），待审核"
            set_tracking(self.s, title, status, reason=reason, actor="system", run_id=self.run_id)
            self._apply_themes(title, sc)
            self.s.flush()
            self._sync_seasons(title, tv, per_episode=False, since_year=None, tr=None)
            tr.new.append(self._new_item(title, tv, sc))
            self.commit()
            if n % 50 == 0:
                self.progress(f"[{tr.label}] 已处理 {n}/{len(ids)}")

    # ---------- 作品 ----------

    def _find_title(self, tv_id: int) -> Title | None:
        ref = self.s.scalar(
            select(ExternalRef).where(
                ExternalRef.source == "tmdb", ExternalRef.external_id == f"tv/{tv_id}"
            )
        )
        return self.s.get(Title, ref.entity_id) if ref else None

    def _brand(self, code: str | None) -> Brand | None:
        return self.s.scalar(select(Brand).where(Brand.code == code)) if code else None

    def _create_title(self, tv: TmdbSeries, sc: Screening, *, brand, via: str) -> Title:
        title = Title(kind="series", discovered_via=via, tracking_status="", producers=[])
        title.brand = brand
        self._fill(title, tv, sc)
        self.s.add(title)
        self.s.flush()
        self._ref("title", title.id, f"tv/{tv.tmdb_id}", "tmdb")
        if tv.imdb_id:
            self._ref("title", title.id, tv.imdb_id, "imdb")
        self._rating(title, tv)
        return title

    def _update_title(self, title: Title, tv: TmdbSeries, sc: Screening) -> None:
        self._fill(title, tv, sc)
        if tv.imdb_id and not self.s.scalar(
            select(ExternalRef).where(
                ExternalRef.source == "imdb", ExternalRef.external_id == tv.imdb_id
            )
        ):
            self._ref("title", title.id, tv.imdb_id, "imdb")
        self._rating(title, tv)

    def _fill(self, title: Title, tv: TmdbSeries, sc: Screening) -> None:
        title.title_en = tv.name_en
        title.title_zh = tv.name_zh
        title.title_original = tv.original_name
        title.original_language = tv.original_language
        title.release_date = tv.first_air_date
        title.year = tv.first_air_date.year if tv.first_air_date else None
        title.overview_en = tv.overview_en
        title.overview_zh = tv.overview_zh
        title.poster_path = tv.poster_path
        title.producers = [name for _id, name in tv.companies if name]
        title.upcoming_date = tv.next_air_date
        title.screen_suggestion = sc.suggestion
        title.screen_reasons = sc.reasons

    def _ref(self, entity_type: str, entity_id: int, external_id: str, source: str) -> None:
        exists = self.s.scalar(
            select(ExternalRef).where(
                ExternalRef.source == source, ExternalRef.external_id == external_id
            )
        )
        if exists:
            return  # 同一个编号只对应一个实体（data-model.md 第 2.3 节）
        self.s.add(
            ExternalRef(
                entity_type=entity_type,
                entity_id=entity_id,
                source=source,
                external_id=external_id,
                match_method="source",
            )
        )

    def _rating(self, title: Title, tv: TmdbSeries) -> None:
        if not tv.vote_count:
            return
        record_rating(self.s, "title", title.id, "tmdb", tv.vote_average, tv.vote_count)

    def _apply_themes(self, title: Title, sc: Screening) -> None:
        have = {tt.theme_id for tt in title.themes}
        for key, origin in sc.themes.items():
            tid = self.theme_ids.get(key)
            if tid and tid not in have:
                title.themes.append(
                    TitleTheme(theme_id=tid, origin=origin, confirmed=origin == "preset")
                )

    def _new_item(self, title: Title, tv: TmdbSeries, sc: Screening) -> NewItem:
        return NewItem(
            tmdb_id=tv.tmdb_id,
            title=title.display_title,
            year=title.year,
            status=title.tracking_status,
            suggestion=sc.suggestion,
            reasons=sc.reasons,
        )

    # ---------- 季、集 ----------

    def _sync_seasons(
        self,
        title: Title,
        tv: TmdbSeries,
        *,
        per_episode: bool,
        since_year: int | None,
        tr: TargetResult | None,
    ) -> None:
        existing = {se.season_number: se for se in title.seasons}
        latest = max((x.number for x in tv.seasons if x.number > 0), default=0)
        for ts in tv.seasons:
            if ts.number == 0:  # 第 0 季是特辑，默认不收（source-mapping.md 第 2.2 节）
                continue
            if since_year and ts.air_date and ts.air_date.year < since_year:
                continue
            se = existing.get(ts.number)
            is_new = se is None
            if is_new:
                se = Season(
                    season_number=ts.number, library_status=None if per_episode else MISSING
                )
                title.seasons.append(se)
                if tr:
                    tr.seasons_added += 1
            changed = se.episode_count != ts.episode_count
            se.name, se.air_date, se.episode_count = ts.name, ts.air_date, ts.episode_count
            self.s.flush()
            if ts.tmdb_id:
                self._ref("season", se.id, f"season/{ts.tmdb_id}", "tmdb")
            # 长青栏目取集：新季、集数变了、或最新一季（可能还在播）才重新取，省请求
            if per_episode and (is_new or changed or ts.number == latest):
                self._sync_episodes(tv.tmdb_id, se, since_year, tr)

    def _sync_episodes(
        self, tv_id: int, se: Season, since_year: int | None, tr: TargetResult | None
    ) -> None:
        episodes = self.tmdb.season(tv_id, se.season_number)
        existing = {e.episode_number: e for e in se.episodes}
        for te in episodes:
            if since_year and te.air_date and te.air_date.year < since_year:
                continue
            ep = existing.get(te.number)
            if ep is None:
                ep = Episode(episode_number=te.number, library_status=MISSING)
                se.episodes.append(ep)
                if tr:
                    tr.episodes_added += 1
            ep.name_en, ep.air_date = te.name, te.air_date
            ep.runtime_min, ep.overview = te.runtime, te.overview
            self.s.flush()
            if te.tmdb_id:
                self._ref("episode", ep.id, f"episode/{te.tmdb_id}", "tmdb")


def record_rating(
    s: Session,
    entity_type: str,
    entity_id: int,
    source: str,
    score: float | None,
    votes: int | None,
    origin: str = "auto",
) -> None:
    """分数或人数变了才新增一行；没变只更新确认时间（data-model.md 第 2.3 节）。"""
    last = s.scalar(
        select(Rating)
        .where(
            Rating.entity_type == entity_type,
            Rating.entity_id == entity_id,
            Rating.source == source,
        )
        .order_by(Rating.id.desc())
        .limit(1)
    )
    now = utcnow()
    if last and last.score == score and last.votes == votes:
        last.confirmed_at = now
        return
    s.add(
        Rating(
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
            score=score,
            votes=votes,
            fetched_at=now,
            confirmed_at=now,
            origin=origin,
        )
    )
