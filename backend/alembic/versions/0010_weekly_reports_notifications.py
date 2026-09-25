"""weekly reports and notifications

Revision ID: 0010_weekly_reports_notifications
Revises: 0009_admin_abuse_controls
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_weekly_reports_notifications"
down_revision = "0009_admin_abuse_controls"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("weekly_reports"):
        op.create_table(
            "weekly_reports",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("week_start", sa.DateTime(), nullable=False),
            sa.Column("week_end", sa.DateTime(), nullable=False),
            sa.Column("summary_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_report_user_week"),
        )
        op.create_index("ix_weekly_reports_user_id", "weekly_reports", ["user_id"])
        op.create_index("ix_weekly_reports_week_start", "weekly_reports", ["week_start"])
        op.create_index("ix_weekly_reports_week_end", "weekly_reports", ["week_end"])
        op.create_index("ix_weekly_reports_created_at", "weekly_reports", ["created_at"])

    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(64), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=True),
            sa.Column("entity_id", sa.String(80), nullable=True),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_kind", "notifications", ["kind"])
        op.create_index("ix_notifications_read_at", "notifications", ["read_at"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("notifications"):
        op.drop_table("notifications")
    if inspector.has_table("weekly_reports"):
        op.drop_table("weekly_reports")
