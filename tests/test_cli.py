from typer.testing import CliRunner

from documentary import __version__, cli
from documentary.core.db import make_engine, recent_runs

runner = CliRunner()


def _use(monkeypatch, settings):
    monkeypatch.setattr(cli, "load_settings", lambda: settings)


def test_version():
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__ == "0.0.0"


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
