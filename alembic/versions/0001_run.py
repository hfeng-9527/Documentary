"""迭代 0：运行记录表 run

Revision ID: 0001
Revises:
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("trigger", sa.String(10), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("report_path", sa.String(300), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("run")
