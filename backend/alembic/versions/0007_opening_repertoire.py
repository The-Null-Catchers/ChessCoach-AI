"""opening repertoire trainer

Revision ID: 0007_opening_repertoire
Revises: 0006_auth_action_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_opening_repertoire"
down_revision = "0006_auth_action_tokens"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if not _has_table("opening_repertoires"):
        op.create_table(
            "opening_repertoires",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("color", sa.String(5), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "name", "color", name="uq_user_repertoire_name_color"),
        )
        op.create_index("ix_opening_repertoires_user_id", "opening_repertoires", ["user_id"])
        op.create_index("ix_opening_repertoires_color", "opening_repertoires", ["color"])

    if not _has_table("opening_lines"):
        op.create_table(
            "opening_lines",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("repertoire_id", sa.String(36), sa.ForeignKey("opening_repertoires.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_id", sa.String(36), sa.ForeignKey("opening_lines.id", ondelete="CASCADE"), nullable=True),
            sa.Column("ply", sa.Integer(), nullable=False),
            sa.Column("fen_before", sa.String(120), nullable=False),
            sa.Column("move_uci", sa.String(8), nullable=False),
            sa.Column("move_san", sa.String(32), nullable=False),
            sa.Column("trainable", sa.Boolean(), nullable=False),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("repetitions", sa.Integer(), nullable=False),
            sa.Column("interval_days", sa.Integer(), nullable=False),
            sa.Column("ease_factor", sa.Float(), nullable=False),
            sa.Column("lapses", sa.Integer(), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("mastery", sa.Float(), nullable=False),
            sa.UniqueConstraint("repertoire_id", "parent_id", "move_uci", name="uq_repertoire_parent_move"),
        )
        op.create_index("ix_opening_lines_repertoire_id", "opening_lines", ["repertoire_id"])
        op.create_index("ix_opening_lines_parent_id", "opening_lines", ["parent_id"])
        op.create_index("ix_opening_lines_ply", "opening_lines", ["ply"])
        op.create_index("ix_opening_lines_trainable", "opening_lines", ["trainable"])
        op.create_index("ix_opening_lines_due_at", "opening_lines", ["due_at"])

    if not _has_table("opening_line_attempts"):
        op.create_table(
            "opening_line_attempts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("line_id", sa.String(36), sa.ForeignKey("opening_lines.id", ondelete="CASCADE"), nullable=False),
            sa.Column("move_uci", sa.String(8), nullable=False),
            sa.Column("correct", sa.Boolean(), nullable=False),
            sa.Column("grade", sa.String(16), nullable=False),
            sa.Column("attempted_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_opening_line_attempts_user_id", "opening_line_attempts", ["user_id"])
        op.create_index("ix_opening_line_attempts_line_id", "opening_line_attempts", ["line_id"])
        op.create_index("ix_opening_line_attempts_attempted_at", "opening_line_attempts", ["attempted_at"])


def downgrade():
    if _has_table("opening_line_attempts"):
        op.drop_table("opening_line_attempts")
    if _has_table("opening_lines"):
        op.drop_table("opening_lines")
    if _has_table("opening_repertoires"):
        op.drop_table("opening_repertoires")
