"""SQLite 数据库：连接（WAL 模式）、表结构迁移（Alembic）、运行记录。"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session

from documentary.core.config import PROJECT_ROOT, Settings
from documentary.core.models import Run, utcnow


def make_engine(settings: Settings) -> Engine:
    engine = create_engine(f"sqlite:///{settings.db_path.as_posix()}")

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _record):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def _alembic_config(settings: Settings) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    cfg.attributes["settings"] = settings
    return cfg


@dataclass
class DbStatus:
    exists: bool
    current: str | None
    head: str

    @property
    def up_to_date(self) -> bool:
        return self.exists and self.current == self.head


def db_status(settings: Settings) -> DbStatus:
    head = ScriptDirectory.from_config(_alembic_config(settings)).get_current_head()
    if not settings.db_path.exists():
        return DbStatus(False, None, head)
    engine = make_engine(settings)
    try:
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
    return DbStatus(True, current, head)


def upgrade(settings: Settings) -> tuple[DbStatus, str | None]:
    """建库或升级到最新表结构。已有数据库且需要升级时先备份，返回备份文件路径。"""
    before = db_status(settings)
    backup = None
    if before.exists and not before.up_to_date:
        backup_dir = settings.data_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        target = backup_dir / f"documentary-{stamp}-before-upgrade.db"
        _backup_sqlite(settings, target)
        backup = str(target)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    command.upgrade(_alembic_config(settings), "head")
    return db_status(settings), backup


def _backup_sqlite(settings: Settings, target) -> None:
    # 先把 WAL 写回主文件，再整个拷贝
    engine = make_engine(settings)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        engine.dispose()
    shutil.copy2(settings.db_path, target)


@contextmanager
def record_run(
    engine: Engine, task: str, trigger: str = "cli", params: dict[str, Any] | None = None
) -> Iterator[Run]:
    """记一条运行记录。代码块里可以改 run.stats、run.status；抛异常时记为 failed。"""
    with Session(engine, expire_on_commit=False) as s:
        run = Run(task=task, trigger=trigger, params=params or {}, status="running", stats={})
        s.add(run)
        s.commit()
        try:
            yield run
        except BaseException:
            run.status = "failed"
            raise
        else:
            if run.status == "running":
                run.status = "success"
        finally:
            run.finished_at = utcnow()
            run.stats = dict(run.stats)  # 重新赋值，保证改动被保存
            s.commit()


def recent_runs(engine: Engine, limit: int = 10) -> list[Run]:
    with Session(engine) as s:
        return list(s.scalars(select(Run).order_by(Run.id.desc()).limit(limit)))
