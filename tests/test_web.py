from fastapi.testclient import TestClient

from documentary.core.db import make_engine, record_run, upgrade
from documentary.web.app import create_app


def test_health(settings):
    client = TestClient(create_app(settings))
    assert client.get("/health").text == "ok"


def test_index_without_db(settings):
    r = TestClient(create_app(settings)).get("/")
    assert r.status_code == 200
    assert "未初始化" in r.text
    assert "doc db upgrade" in r.text


def test_index_shows_config_and_runs(settings):
    upgrade(settings)
    engine = make_engine(settings)
    with record_run(engine, "check-config"):
        pass
    engine.dispose()
    r = TestClient(create_app(settings)).get("/")
    assert r.status_code == 200
    assert "v0.0.0" in r.text
    assert "通过" in r.text and "brands.yaml" in r.text
    assert "check-config" in r.text and "成功" in r.text


def test_static_htmx(settings):
    r = TestClient(create_app(settings)).get("/static/htmx.min.js")
    assert r.status_code == 200 and "htmx" in r.text[:200]
