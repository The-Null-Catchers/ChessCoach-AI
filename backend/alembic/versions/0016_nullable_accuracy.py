"""Allow unavailable opening and endgame accuracy."""

from alembic import op

revision = "0016_nullable_accuracy"
down_revision = "0015_ai_usage_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("opening_stats", "endgame_stats"):
        op.alter_column(table, "avg_accuracy", nullable=True)


def downgrade() -> None:
    for table in ("opening_stats", "endgame_stats"):
        op.execute(f"UPDATE {table} SET avg_accuracy = 0 WHERE avg_accuracy IS NULL")
        op.alter_column(table, "avg_accuracy", nullable=False)
