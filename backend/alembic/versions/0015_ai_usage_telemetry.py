"""AI provider usage telemetry

Revision ID: 0015_ai_usage_telemetry
Revises: 0014_push_notifications
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_ai_usage_telemetry"
down_revision = "0014_push_notifications"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_usage_events" in set(inspector.get_table_names()):
        return

    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("move_id", sa.String(36), sa.ForeignKey("moves.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("operation", sa.String(48), nullable=False, server_default="coach_explanation"),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_id", sa.String(160), nullable=True),
        sa.Column("error_type", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_usage_events_user_id", "ai_usage_events", ["user_id"])
    op.create_index("ix_ai_usage_events_move_id", "ai_usage_events", ["move_id"])
    op.create_index("ix_ai_usage_events_provider", "ai_usage_events", ["provider"])
    op.create_index("ix_ai_usage_events_model", "ai_usage_events", ["model"])
    op.create_index("ix_ai_usage_events_operation", "ai_usage_events", ["operation"])
    op.create_index("ix_ai_usage_events_status", "ai_usage_events", ["status"])
    op.create_index("ix_ai_usage_events_created_at", "ai_usage_events", ["created_at"])
    op.create_index("ix_ai_usage_provider_created", "ai_usage_events", ["provider", "created_at"])
    op.create_index("ix_ai_usage_status_created", "ai_usage_events", ["status", "created_at"])


def downgrade():
    bind = op.get_bind()
    if "ai_usage_events" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("ai_usage_events")
