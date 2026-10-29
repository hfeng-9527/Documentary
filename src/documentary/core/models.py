"""数据表（data-model.md）。按迭代逐步建表，迭代 0 只有 `run`。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
