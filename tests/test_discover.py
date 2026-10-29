from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tmdb_mock import FakeTmdb

from documentary.core.config import load_catalog
from documentary.core.db import make_engine, upgrade
from documentary.core.http import SourceError
from documentary.core.models import (
    Episode,
    ExternalRef,
    Rating,
    Season,
    SourceCheckpoint,
    StatusEvent,
    Title,
)
from documentary.core.raw import RawStore
from documentary.pipeline.discover import discover_tmdb

TODAY = date(2026, 10, 29)


@pytest.fixture
def env(tmdb_settings):
    upgrade(tmdb_settings)
    engine = make_engine(tmdb_settings)
    fake = FakeTmdb()

    def run(**kw):
        return discover_tmdb(
            engine,
            tmdb_settings,
            load_catalog(tmdb_settings.config_dir),
            transport=fake.transport(),
            sleep=lambda _s: None,
            today=TODAY,
            **kw,
        )

    yield engine, fake, run
    engine.dispose()


def _title(s, tv_id) -> Title:
    ref = s.scalar(select(ExternalRef).where(ExternalRef.external_id == f"tv/{tv_id}"))
    return s.get(Title, ref.entity_id)


def test_full_run(env, tmdb_settings):
    engine, fake, run = env
    result = run()
    assert result.status == "success", [t.error for t in result.targets]
    keys = [t.key for t in result.targets]
    # 重点栏目在前，品牌在后；只跑试点
    assert keys == [
        "series:nova",
        "series:horizon",
        "series:inside-the-factory",
        "brand:UK-2",
        "brand:ST-1",
    ]
    by = {t.key: t for t in result.targets}
    # 播出方两页 + 出品公司一页，900101 两边都有，只算一次
    assert by["brand:UK-2"].found == 4 and len(by["brand:UK-2"].new) == 4
    assert by["brand:UK-2"].since == date(2010, 1, 1)
    assert len(by["brand:ST-1"].new) == 5

    with Session(engine) as s:
        pe2 = _title(s, 68595)
        assert pe2.tracking_status == "pending" and pe2.brand.code == "UK-2"
        assert pe2.title_zh == "地球脉动 第二季" and pe2.title_en == "Planet Earth II"
        assert pe2.screen_suggestion == "include"
        # 品牌默认“自然”，关键词又命中“野生动物”：只留更细的子类
        assert {tt.theme.key for tt in pe2.themes} == {"nature.wildlife"}
        assert _title(s, 900103).themes[0].theme.key == "nature"  # 只有品牌默认
        assert [se.season_number for se in pe2.seasons] == [1]  # 第 0 季不收
        assert pe2.seasons[0].library_status == "missing"
        assert s.scalar(select(ExternalRef).where(ExternalRef.external_id == "tt5491994"))
        r = s.scalar(select(Rating).where(Rating.entity_id == pe2.id))
        assert (r.source, r.score, r.votes) == ("tmdb", 9.1, 1650)
        # 台湾译名也能用
        assert _title(s, 900101).title_zh == "七个世界，一个星球"
        # 首播日期在未来 → 待播
        assert _title(s, 900102).tracking_status == "upcoming"

        crime = _title(s, 900202)
        assert crime.screen_suggestion == "exclude"
        assert any("真实犯罪" in r for r in crime.screen_reasons)
        spanish = _title(s, 900203)
        assert spanish.screen_suggestion == "exclude"
        assert any("非中英原产" in r for r in spanish.screen_reasons)
        unknown = _title(s, 900204)
        assert unknown.screen_suggestion is None
        assert unknown.screen_reasons == ["未判断出主题，需人工"]
        money = _title(s, 900205)
        assert money.screen_suggestion == "include"
        assert "economics.finance" in {tt.theme.key for tt in money.themes}

        nova = _title(s, 3562)
        assert nova.tracking_status == "included" and nova.per_episode
        assert nova.series_watch.key == "nova"
        # 2010 年以前的季不收；季上不记片源状态，集上记
        assert [se.season_number for se in nova.seasons] == [37, 52]
        assert nova.seasons[0].library_status is None
        assert [e.episode_number for e in nova.seasons[0].episodes] == [1, 2, 3]
        assert nova.seasons[0].episodes[0].library_status == "missing"
        assert [tt.theme.key for tt in nova.themes] == ["science"]

        events = s.scalars(
            select(StatusEvent).where(
                StatusEvent.entity_id == nova.id, StatusEvent.field == "tracking"
            )
        ).all()
        assert [(e.old_value, e.new_value, e.actor) for e in events] == [
            (None, "included", "system")
        ]
        assert s.scalar(select(func.count()).select_from(SourceCheckpoint)) == 5

    with RawStore(tmdb_settings.raw_db_path) as raw:
        assert raw.get("tmdb", "tv", "68595")["name"] == "Planet Earth II"
        assert raw.get("tmdb", "season", "3562/37")["season_number"] == 37


def test_second_run_adds_nothing(env):
    engine, fake, run = env
    run()
    with Session(engine) as s:
        counts = (
            s.scalar(select(func.count()).select_from(Title)),
            s.scalar(select(func.count()).select_from(Season)),
            s.scalar(select(func.count()).select_from(Episode)),
            s.scalar(select(func.count()).select_from(Rating)),
        )
    fake.calls.clear()
    result = run()
    assert result.status == "success"
    assert sum(len(t.new) for t in result.targets) == 0
    by = {t.key: t for t in result.targets}
    # 第二次只查上次成功之前 30 天以后首播的
    assert by["brand:UK-2"].since > date(2020, 1, 1)
    # 已有的作品不再取详情；栏目的旧季不再取集，只取最新一季
    assert "/tv/68595" not in fake.calls
    assert "/tv/3562/season/37" not in fake.calls and "/tv/3562/season/52" in fake.calls
    with Session(engine) as s:
        assert counts == (
            s.scalar(select(func.count()).select_from(Title)),
            s.scalar(select(func.count()).select_from(Season)),
            s.scalar(select(func.count()).select_from(Episode)),
            s.scalar(select(func.count()).select_from(Rating)),
        )


def test_dry_run_writes_nothing(env, tmdb_settings):
    engine, fake, run = env
    result = run(dry_run=True)
    assert result.dry_run and sum(len(t.new) for t in result.targets) == 12
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Title)) == 0
        assert s.scalar(select(func.count()).select_from(SourceCheckpoint)) == 0
    assert not tmdb_settings.raw_db_path.exists()


def test_only_one_brand(env):
    engine, fake, run = env
    result = run(brand="uk-2")
    assert [t.key for t in result.targets] == ["brand:UK-2"]


def test_excluded_title_is_not_rediscovered(env):
    engine, fake, run = env
    run(brand="ST-1")
    with Session(engine) as s:
        _title(s, 900202).tracking_status = "excluded"
        s.query(SourceCheckpoint).delete()  # 让下次从头再查一遍
        s.commit()
    result = run(brand="ST-1")
    assert result.targets[0].new == [] and result.targets[0].known == 5
    with Session(engine) as s:
        assert _title(s, 900202).tracking_status == "excluded"


def test_brand_failure_does_not_stop_others(env):
    engine, fake, run = env
    fake.fail["/tv/900201"] = 500
    result = run()
    by = {t.key: t for t in result.targets}
    assert result.status == "partial"
    assert "HTTP 500" in by["brand:ST-1"].error
    assert by["brand:UK-2"].error is None and len(by["brand:UK-2"].new) == 4
    with Session(engine) as s:
        cp = s.scalar(select(SourceCheckpoint).where(SourceCheckpoint.scope_key == "brand:ST-1"))
        assert cp.last_success_at is None and cp.consecutive_failures == 1
        assert "HTTP 500" in cp.last_error
        ok = s.scalar(select(SourceCheckpoint).where(SourceCheckpoint.scope_key == "brand:UK-2"))
        assert ok.last_success_at is not None


def test_bad_key_stops_everything(env, tmdb_settings):
    engine, fake, run = env
    fake.key = "something-else"
    result = run()
    assert result.status == "failed"
    assert "401" in result.fatal and "TMDB_API_KEY" in result.fatal
    assert result.targets[0].error and all(t.skipped for t in result.targets[1:])
    assert len(fake.calls) == 1  # 401 不重试


def test_missing_key(tmdb_settings):
    settings = tmdb_settings.model_copy(update={"tmdb_api_key": None})
    upgrade(settings)
    engine = make_engine(settings)
    with pytest.raises(SourceError, match="缺 TMDB_API_KEY"):
        discover_tmdb(engine, settings, load_catalog(settings.config_dir))
    engine.dispose()
