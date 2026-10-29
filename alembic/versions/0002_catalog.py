"""迭代 1：品牌、栏目、主题、作品、季、集、编号、作品主题、评分、状态变化、检查进度；标题全文检索

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brand",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("tmdb_networks", sa.JSON(), nullable=False),
        sa.Column("tmdb_companies", sa.JSON(), nullable=False),
        sa.Column("default_themes", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "external_ref",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("external_id", sa.String(length=60), nullable=False),
        sa.Column("match_method", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id"),
    )
    with op.batch_alter_table("external_ref", schema=None) as batch_op:
        batch_op.create_index("ix_external_ref_entity", ["entity_type", "entity_id"], unique=False)

    op.create_table(
        "rating",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("votes", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rating", schema=None) as batch_op:
        batch_op.create_index(
            "ix_rating_entity", ["entity_type", "entity_id", "source"], unique=False
        )

    op.create_table(
        "series_watch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tmdb_tv_id", sa.Integer(), nullable=True),
        sa.Column("brand_code", sa.String(length=20), nullable=True),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("per_episode", sa.Boolean(), nullable=False),
        sa.Column("since_year", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "source_checkpoint",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("scope_key", sa.String(length=80), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backfill_cursor", sa.JSON(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "scope_key"),
    )
    op.create_table(
        "theme",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("parent_key", sa.String(length=60), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "status_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=10), nullable=False),
        sa.Column("old_value", sa.String(length=10), nullable=True),
        sa.Column("new_value", sa.String(length=10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=10), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("status_event", schema=None) as batch_op:
        batch_op.create_index("ix_status_event_entity", ["entity_type", "entity_id"], unique=False)

    op.create_table(
        "title",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("title_zh", sa.String(length=500), nullable=True),
        sa.Column("title_original", sa.String(length=500), nullable=True),
        sa.Column("original_language", sa.String(length=10), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("overview_en", sa.Text(), nullable=True),
        sa.Column("overview_zh", sa.Text(), nullable=True),
        sa.Column("runtime_min", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("series_watch_id", sa.Integer(), nullable=True),
        sa.Column("producers", sa.JSON(), nullable=False),
        sa.Column("discovered_via", sa.String(length=20), nullable=False),
        sa.Column("tracking_status", sa.String(length=10), nullable=False),
        sa.Column("tracking_reason", sa.Text(), nullable=True),
        sa.Column("screen_suggestion", sa.String(length=10), nullable=True),
        sa.Column("screen_reasons", sa.JSON(), nullable=False),
        sa.Column("upcoming_date", sa.Date(), nullable=True),
        sa.Column("watch_until", sa.Date(), nullable=True),
        sa.Column("library_status", sa.String(length=10), nullable=True),
        sa.Column("poster_path", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brand.id"],
        ),
        sa.ForeignKeyConstraint(
            ["series_watch_id"],
            ["series_watch.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "season",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("episode_count", sa.Integer(), nullable=True),
        sa.Column("library_status", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title_id", "season_number"),
    )
    with op.batch_alter_table("season", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_season_title_id"), ["title_id"], unique=False)

    op.create_table(
        "title_theme",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("theme_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["theme.id"],
        ),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title_id", "theme_id"),
    )
    with op.batch_alter_table("title_theme", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_title_theme_title_id"), ["title_id"], unique=False)

    op.create_table(
        "episode",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=500), nullable=True),
        sa.Column("name_zh", sa.String(length=500), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("runtime_min", sa.Integer(), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("library_status", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["season.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "episode_number"),
    )
    with op.batch_alter_table("episode", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_episode_season_id"), ["season_id"], unique=False)

    # 标题全文检索（data-model.md 第 4 节）：trigram 分词，三个字及以上可用；
    # 由触发器跟着 title 表更新
    op.execute(
        "CREATE VIRTUAL TABLE title_fts USING fts5("
        "title_en, title_zh, title_original, content='title', content_rowid='id', "
        "tokenize='trigram')"
    )
    op.execute(
        "CREATE TRIGGER title_fts_ai AFTER INSERT ON title BEGIN "
        "INSERT INTO title_fts(rowid, title_en, title_zh, title_original) "
        "VALUES (new.id, new.title_en, new.title_zh, new.title_original); END"
    )
    op.execute(
        "CREATE TRIGGER title_fts_ad AFTER DELETE ON title BEGIN "
        "INSERT INTO title_fts(title_fts, rowid, title_en, title_zh, title_original) "
        "VALUES ('delete', old.id, old.title_en, old.title_zh, old.title_original); END"
    )
    op.execute(
        "CREATE TRIGGER title_fts_au AFTER UPDATE OF title_en, title_zh, title_original ON title "
        "BEGIN "
        "INSERT INTO title_fts(title_fts, rowid, title_en, title_zh, title_original) "
        "VALUES ('delete', old.id, old.title_en, old.title_zh, old.title_original); "
        "INSERT INTO title_fts(rowid, title_en, title_zh, title_original) "
        "VALUES (new.id, new.title_en, new.title_zh, new.title_original); END"
    )


def downgrade() -> None:
    for trg in ("title_fts_ai", "title_fts_ad", "title_fts_au"):
        op.execute(f"DROP TRIGGER IF EXISTS {trg}")
    op.execute("DROP TABLE IF EXISTS title_fts")
    with op.batch_alter_table("episode", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_episode_season_id"))

    op.drop_table("episode")
    with op.batch_alter_table("title_theme", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_title_theme_title_id"))

    op.drop_table("title_theme")
    with op.batch_alter_table("season", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_season_title_id"))

    op.drop_table("season")
    op.drop_table("title")
    with op.batch_alter_table("status_event", schema=None) as batch_op:
        batch_op.drop_index("ix_status_event_entity")

    op.drop_table("status_event")
    op.drop_table("theme")
    op.drop_table("source_checkpoint")
    op.drop_table("series_watch")
    with op.batch_alter_table("rating", schema=None) as batch_op:
        batch_op.drop_index("ix_rating_entity")

    op.drop_table("rating")
    with op.batch_alter_table("external_ref", schema=None) as batch_op:
        batch_op.drop_index("ix_external_ref_entity")

    op.drop_table("external_ref")
    op.drop_table("brand")
