"""feature flags

Revision ID: 0011_feature_flags
Revises: 0010_weekly_reports
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_feature_flags"
down_revision = "0010_weekly_reports"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("key", sa.String(80), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column(
                "updated_by_user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_feature_flags_enabled", "feature_flags", ["enabled"])
        op.create_index("ix_feature_flags_updated_by_user_id", "feature_flags", ["updated_by_user_id"])
        op.create_index("ix_feature_flags_updated_at", "feature_flags", ["updated_at"])


def downgrade():
    if sa.inspect(op.get_bind()).has_table("feature_flags"):
        op.drop_table("feature_flags")
