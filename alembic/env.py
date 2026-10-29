"""Alembic 迁移环境。数据库地址从 Settings 读取（`doc db upgrade` 会传进来）。"""

from alembic import context

from documentary.core.config import load_settings
from documentary.core.db import make_engine
from documentary.core.models import Base

settings = context.config.attributes.get("settings") or load_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = make_engine(settings)
with engine.connect() as connection:
    # SQLite 改表结构需要 batch 模式
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
