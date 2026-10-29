from typer.testing import CliRunner

from documentary import __version__, cli
from documentary.core.db import make_engine, recent_runs

runner = CliRunner()


def _use(monkeypatch, settings):
    monkeypatch.setattr(cli, "load_settings", lambda: settings)


def test_version():
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__ == "0.1.0"


def test_check_config_records_run(monkeypatch, settings):
    _use(monkeypatch, settings)
    assert runner.invoke(cli.app, ["db", "upgrade"]).exit_code == 0
    result = runner.invoke(cli.app, ["check-config"])
    assert result.exit_code == 0, result.output
    assert "配置检查通过" in result.output
    engine = make_engine(settings)
    runs = recent_runs(engine)
    engine.dispose()
    assert [(r.task, r.status, r.trigger) for r in runs] == [("check-config", "success", "cli")]


def test_check_config_without_db_still_checks(monkeypatch, settings):
    _use(monkeypatch, settings)
    result = runner.invoke(cli.app, ["check-config"])
    assert result.exit_code == 0
    assert "先运行 doc db upgrade" in result.output


def test_check_config_fails_on_error(monkeypatch, settings):
    _use(monkeypatch, settings)
    runner.invoke(cli.app, ["db", "upgrade"])
    p = settings.config_dir / "brands.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("[nature]", "[natur]"), encoding="utf-8")
    result = runner.invoke(cli.app, ["check-config"])
    assert result.exit_code == 1
    assert "natur 不在 themes.yaml 里" in result.output
    engine = make_engine(settings)
    assert recent_runs(engine)[0].status == "failed"
    engine.dispose()


def _fake_tmdb(monkeypatch, fake):
    from functools import partial

    from documentary.pipeline import discover

    monkeypatch.setattr(
        discover,
        "discover_tmdb",
        partial(discover.discover_tmdb, transport=fake.transport(), sleep=lambda _s: None),
    )


def test_discover_dry_run_then_real(monkeypatch, tmdb_settings):
    from tmdb_mock import FakeTmdb

    _use(monkeypatch, tmdb_settings)
    _fake_tmdb(monkeypatch, FakeTmdb())
    runner.invoke(cli.app, ["db", "upgrade"])

    result = runner.invoke(cli.app, ["discover", "--source", "tmdb", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "会新增 12 条" in result.output and "dry-run：没有写数据库" in result.output
    assert "Small Town Murders" in result.output and "建议排除" in result.output
    engine = make_engine(tmdb_settings)
    assert recent_runs(engine) == []  # dry-run 不记运行记录

    result = runner.invoke(cli.app, ["discover"])
    assert result.exit_code == 0, result.output
    assert "合计新增 12 条" in result.output and "✓ 完成" in result.output
    result = runner.invoke(cli.app, ["discover", "--brand", "UK-2"])
    assert "合计新增 0 条" in result.output
    runs = recent_runs(engine)
    engine.dispose()
    assert [(r.task, r.status) for r in runs] == [("discover", "success")] * 2
    assert runs[1].stats["new"] == 12 and runs[1].stats["targets"]["brand:ST-1"]["new"] == 5


def test_discover_bad_key(monkeypatch, tmdb_settings):
    from tmdb_mock import FakeTmdb

    _use(monkeypatch, tmdb_settings)
    _fake_tmdb(monkeypatch, FakeTmdb(key="another"))
    runner.invoke(cli.app, ["db", "upgrade"])
    result = runner.invoke(cli.app, ["discover", "--brand", "UK-2"])
    assert result.exit_code == 1
    assert "TMDB 拒绝了 API key（401），请检查 .env 的 TMDB_API_KEY" in result.output
    assert tmdb_settings.tmdb_api_key not in result.output
    engine = make_engine(tmdb_settings)
    assert recent_runs(engine)[0].status == "failed"
    engine.dispose()


def test_discover_missing_key(monkeypatch, settings):
    _use(monkeypatch, settings)
    runner.invoke(cli.app, ["db", "upgrade"])
    result = runner.invoke(cli.app, ["discover"])
    assert result.exit_code == 1 and "缺 TMDB_API_KEY" in result.output


def test_discover_unknown_brand(monkeypatch, tmdb_settings):
    _use(monkeypatch, tmdb_settings)
    runner.invoke(cli.app, ["db", "upgrade"])
    result = runner.invoke(cli.app, ["discover", "--brand", "XX-9"])
    assert result.exit_code == 2 and "没有编号为 XX-9" in result.output


def test_discover_needs_db(monkeypatch, tmdb_settings):
    _use(monkeypatch, tmdb_settings)
    result = runner.invoke(cli.app, ["discover"])
    assert result.exit_code == 1 and "doc db upgrade" in result.output
