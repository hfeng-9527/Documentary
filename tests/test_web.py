from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tmdb_mock import FakeTmdb

from documentary.core.config import load_catalog
from documentary.core.db import make_engine, record_run, upgrade
from documentary.core.models import Episode, ExternalRef, Season, StatusEvent, Title
from documentary.pipeline.discover import discover_tmdb
from documentary.web.app import create_app

HX = {"HX-Request": "true"}


def test_health(settings):
    client = TestClient(create_app(settings))
    assert client.get("/health").text == "ok"


def test_index_without_db(settings):
    r = TestClient(create_app(settings)).get("/")
    assert r.status_code == 200
    assert "未初始化" in r.text
    assert "doc db upgrade" in r.text


def test_pages_without_db_say_upgrade(settings):
    r = TestClient(create_app(settings)).get("/titles")
    assert r.status_code == 503 and "doc db upgrade" in r.text


def test_index_shows_config_and_runs(settings):
    upgrade(settings)
    engine = make_engine(settings)
    with record_run(engine, "check-config"):
        pass
    engine.dispose()
    r = TestClient(create_app(settings)).get("/")
    assert r.status_code == 200
    assert "v0.1.0" in r.text
    assert "通过" in r.text and "brands.yaml" in r.text
    assert "check-config" in r.text and "成功" in r.text
    assert "还没有采集过数据" in r.text


def test_static_htmx(settings):
    r = TestClient(create_app(settings)).get("/static/htmx.min.js")
    assert r.status_code == 200 and "htmx" in r.text[:200]


# ---------- 有数据以后 ----------


@pytest.fixture
def app(tmdb_settings):
    upgrade(tmdb_settings)
    engine = make_engine(tmdb_settings)
    with record_run(engine, "discover") as run:
        result = discover_tmdb(
            engine,
            tmdb_settings,
            load_catalog(tmdb_settings.config_dir),
            run_id=run.id,
            transport=FakeTmdb().transport(),
            sleep=lambda _s: None,
            today=date(2026, 10, 29),
        )
        run.stats = result.stats()
    client = TestClient(create_app(tmdb_settings))
    yield client, engine
    engine.dispose()


def _id(engine, tv_id) -> int:
    with Session(engine) as s:
        return s.scalar(
            select(ExternalRef.entity_id).where(ExternalRef.external_id == f"tv/{tv_id}")
        )


def _status(engine, tv_id) -> str:
    with Session(engine) as s:
        return s.get(Title, _id(engine, tv_id)).tracking_status


def test_index_counts(app):
    client, _ = app
    r = client.get("/")
    assert "待审核" in r.text and "新增 12 条" in r.text
    # BBC Earth 4 部（其中 1 部待播）+ Netflix 5 部 = 待审核 8；三个重点栏目已收录
    assert "<b>8</b>待审核" in r.text and "<b>3</b>已收录" in r.text and "<b>1</b>待播" in r.text


def test_review_page_groups_by_brand(app):
    client, _ = app
    r = client.get("/review")
    assert "UK-2 BBC Natural History Unit / BBC Earth" in r.text and "ST-1 Netflix" in r.text
    assert "疑似真实犯罪" in r.text and "非中英原产" in r.text and "未判断出主题" in r.text
    assert "地球脉动 第二季" in r.text
    assert "Frozen Frontier" not in r.text  # 待播的不进审核


def test_review_include_and_exclude(app):
    client, engine = app
    pe2 = _id(engine, 68595)
    r = client.post(f"/review/{pe2}", data={"action": "include"}, headers=HX)
    assert r.status_code == 200 and "已收录" in r.text
    assert _status(engine, 68595) == "included"

    crime = _id(engine, 900202)
    client.post(f"/review/{crime}", data={"action": "exclude", "reason": "真实犯罪"}, headers=HX)
    with Session(engine) as s:
        assert s.get(Title, crime).tracking_status == "excluded"
        ev = s.scalars(
            select(StatusEvent).where(StatusEvent.entity_id == crime).order_by(StatusEvent.id)
        ).all()[-1]
        assert (ev.old_value, ev.new_value, ev.actor, ev.reason) == (
            "pending",
            "excluded",
            "manual",
            "真实犯罪",
        )


def test_review_include_with_themes(app):
    client, engine = app
    unknown = _id(engine, 900204)
    client.post(
        f"/review/{unknown}",
        data={"action": "include", "edit_themes": "1", "themes": ["history", "history.war"]},
    )
    with Session(engine) as s:
        t = s.get(Title, unknown)
        assert t.tracking_status == "included"
        assert {(tt.theme.key, tt.origin, tt.confirmed) for tt in t.themes} == {
            ("history", "manual", True),
            ("history.war", "manual", True),
        }


def test_review_group(app):
    client, engine = app
    with Session(engine) as s:
        netflix = s.get(Title, _id(engine, 900201)).brand_id
    client.post("/review-group", data={"brand_id": netflix, "mode": "suggested"})
    assert _status(engine, 900201) == "included"  # 建议收录
    assert _status(engine, 900205) == "included"
    assert _status(engine, 900202) == "excluded"  # 建议排除
    assert _status(engine, 900203) == "excluded"
    assert _status(engine, 900204) == "pending"  # 需人工，留下
    assert _status(engine, 68595) == "pending"  # 别的品牌不动

    with Session(engine) as s:
        bbc = s.get(Title, _id(engine, 68595)).brand_id
    client.post("/review-group", data={"brand_id": bbc, "mode": "all"})
    assert _status(engine, 68595) == "included" and _status(engine, 900103) == "included"
    assert _status(engine, 900102) == "upcoming"  # 待播的不受影响


def test_titles_list_and_filters(app):
    client, engine = app
    r = client.get("/titles")
    assert "NOVA" in r.text and "Horizon" in r.text and "工厂大揭秘" in r.text
    assert "Planet Earth II" not in r.text  # 还没收录
    r = client.get("/titles", params={"theme": "engineering"})
    assert "工厂大揭秘" in r.text and "NOVA" not in r.text
    r = client.get("/titles", params={"status": "pending", "brand": "ST-1"})
    assert "我们的星球" in r.text and "地球脉动" not in r.text
    r = client.get("/titles", params={"year_from": "1970", "year_to": "1970"})
    assert "没有符合条件的作品" in r.text


def test_to_download_sorted_by_rating(app):
    client, engine = app
    client.post("/review-group", data={"brand_id": "", "mode": "all"})  # 没有品牌的组：空操作
    with Session(engine) as s:
        bbc = s.get(Title, _id(engine, 68595)).brand_id
    client.post("/review-group", data={"brand_id": bbc, "mode": "all"})
    text = client.get("/to-download").text
    # 地球脉动 II（9.1）在 NOVA（7.9）前面
    assert text.index("地球脉动 第二季") < text.index("新星") < text.index("工厂大揭秘")


def test_library_marking(app):
    client, engine = app
    with Session(engine) as s:
        bbc = s.get(Title, _id(engine, 68595)).brand_id
    client.post("/review-group", data={"brand_id": bbc, "mode": "all"})
    pe2 = _id(engine, 68595)
    with Session(engine) as s:
        season = s.scalar(select(Season).where(Season.title_id == pe2))
    r = client.post(f"/library/season/{season.id}", data={"status": "have"}, headers=HX)
    assert r.status_code == 200 and "全部已入库" in r.text
    r = client.get(f"/title/{pe2}")
    assert "全部已入库（1 季）" in r.text

    # 长青栏目：整季标记计划中，再单独把一集标已入库
    nova = _id(engine, 3562)
    with Session(engine) as s:
        s37 = s.scalar(select(Season).where(Season.title_id == nova, Season.season_number == 37))
        ep1 = s37.episodes[0].id
        s37_id = s37.id
    r = client.post(f"/library/season/{s37_id}/episodes", data={"status": "planned"}, headers=HX)
    assert "计划中 3 集" in r.text
    r = client.post(f"/library/episode/{ep1}", data={"status": "have"}, headers=HX)
    assert "已入库 1 集" in r.text and "计划中 2 集" in r.text
    assert 'id="library"' in r.text and "open" in r.text

    text = client.get("/to-download", params={"library": "planned"}).text
    assert "新星" in text and "地球脉动" not in text
    with Session(engine) as s:
        ev = s.scalar(
            select(StatusEvent)
            .where(StatusEvent.entity_type == "episode", StatusEvent.entity_id == ep1)
            .order_by(StatusEvent.id.desc())
        )
        assert (ev.field, ev.old_value, ev.new_value, ev.actor) == (
            "library",
            "planned",
            "have",
            "manual",
        )


def test_library_mark_whole_title_from_list(app):
    client, engine = app
    itf = _id(engine, 72793)
    r = client.post(f"/library/title/{itf}", data={"status": "planned"}, headers=HX)
    assert r.status_code == 200 and "计划中 2 集" in r.text
    with Session(engine) as s:
        statuses = s.scalars(
            select(Episode.library_status).join(Season).where(Season.title_id == itf)
        ).all()
        assert statuses == ["planned", "planned"]


def test_bad_library_status(app):
    client, engine = app
    with Session(engine) as s:
        sid = s.scalar(select(Season.id))
    assert client.post(f"/library/season/{sid}", data={"status": "oops"}).status_code == 400


def test_detail_page(app):
    client, engine = app
    nova = _id(engine, 3562)
    r = client.get(f"/title/{nova}")
    assert "新星" in r.text and "第 52 季" in r.text and "第 37 季" in r.text
    assert "第 36 季" not in r.text  # 2010 年以前
    assert "Darwin&#39;s Darkest Hour" in r.text
    assert "TMDB 7.9" in r.text and "https://www.imdb.com/title/tt0071034/" in r.text
    assert "重点栏目，直接收录" in r.text and "（新发现）" in r.text
    assert client.get("/title/999999").status_code == 404


def test_change_tracking_and_themes(app):
    client, engine = app
    pe2 = _id(engine, 68595)
    client.post(f"/title/{pe2}/tracking", data={"status": "excluded", "reason": "测试"})
    assert _status(engine, 68595) == "excluded"
    client.post(f"/title/{pe2}/themes", data={"themes": ["nature.ocean"]})
    with Session(engine) as s:
        assert [tt.theme.key for tt in s.get(Title, pe2).themes] == ["nature.ocean"]
    r = client.get(f"/title/{pe2}")
    assert "测试" in r.text and "人工" in r.text


@pytest.mark.parametrize(
    "q, expect",
    [
        ("地球脉动", "地球脉动 第二季"),
        ("Planet Earth", "Planet Earth II"),
        ("planet earth", "Planet Earth III"),
        ("NOVA", "新星"),
        ("新星", "新星"),  # 两个字：模糊匹配
        ("工厂", "工厂大揭秘"),
    ],
)
def test_search(app, q, expect):
    client, _ = app
    r = client.get("/search", params={"q": q})
    assert r.status_code == 200 and expect in r.text, q


def test_search_nothing(app):
    client, _ = app
    assert "没找到" in client.get("/search", params={"q": "不存在的片子"}).text
    assert client.get("/search", params={"q": '"quotes"'}).status_code == 200
