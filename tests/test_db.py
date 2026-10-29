import sqlite3

from alembic import command

from documentary.core.db import (
    _alembic_config,
    db_status,
    make_engine,
    recent_runs,
    record_run,
    upgrade,
)


def test_upgrade_creates_run_table(settings):
    assert not db_status(settings).exists
    status, backup = upgrade(settings)
    assert status.up_to_date and backup is None
    con = sqlite3.connect(settings.db_path)
    cols = {row[1] for row in con.execute("PRAGMA table_info(run)")}
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    con.close()
    assert {"task", "trigger", "params", "status", "started_at", "finished_at", "stats"} <= cols


def test_upgrade_is_idempotent(settings):
    upgrade(settings)
    status, backup = upgrade(settings)
    assert status.up_to_date and backup is None


def test_upgrade_backs_up_outdated_db(settings):
    upgrade(settings)
    # 模拟“还停在上一个版本的旧库”：退回到 0001
    command.downgrade(_alembic_config(settings), "0001")
    assert not db_status(settings).up_to_date
    status, backup = upgrade(settings)
    assert status.up_to_date and status.current == status.head
    assert backup and (settings.data_dir / "backups").exists()


def test_upgrade_creates_iteration1_tables(settings):
    upgrade(settings)
    con = sqlite3.connect(settings.db_path)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert {
        "brand",
        "series_watch",
        "theme",
        "title",
        "season",
        "episode",
        "external_ref",
        "title_theme",
        "rating",
        "status_event",
        "source_checkpoint",
        "title_fts",
    } <= names


def test_record_run(settings):
    upgrade(settings)
    engine = make_engine(settings)
    with record_run(engine, "check-config", params={"x": 1}) as run:
        run.stats = {"n": 3}
    try:
        with record_run(engine, "boom") as run:
            raise RuntimeError("x")
    except RuntimeError:
        pass
    runs = recent_runs(engine)
    engine.dispose()
    assert [(r.task, r.status) for r in runs] == [("boom", "failed"), ("check-config", "success")]
    assert runs[1].stats == {"n": 3} and runs[1].params == {"x": 1}
    assert runs[1].finished_at is not None
