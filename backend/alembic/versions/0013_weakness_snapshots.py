"""historical weakness snapshots

Revision ID: 0013_weakness_snapshots
Revises: 0012_engine_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_weakness_snapshots"
down_revision = "0012_engine_profiles"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "weakness_snapshots" in inspector.get_table_names():
        return

    op.create_table(
        "weakness_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_weakness_snapshots_user_id", "weakness_snapshots", ["user_id"])
    op.create_index("ix_weakness_snapshots_category", "weakness_snapshots", ["category"])
    op.create_index("ix_weakness_snapshots_captured_at", "weakness_snapshots", ["captured_at"])
    op.create_index(
        "ix_weakness_snapshots_user_category_captured",
        "weakness_snapshots",
        ["user_id", "category", "captured_at"],
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "weakness_snapshots" in inspector.get_table_names():
        op.drop_table("weakness_snapshots")
