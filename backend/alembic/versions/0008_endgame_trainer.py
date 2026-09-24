"""endgame trainer

Revision ID: 0008_endgame_trainer
Revises: 0007_opening_repertoire
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_endgame_trainer"
down_revision = "0007_opening_repertoire"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if not _has_table("endgame_exercises"):
        op.create_table(
            "endgame_exercises",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("slug", sa.String(120), nullable=False, unique=True),
            sa.Column("category", sa.String(64), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("objective", sa.Text(), nullable=False),
            sa.Column("fen", sa.String(120), nullable=False),
            sa.Column("solution_uci", sa.String(8), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("difficulty", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_endgame_exercises_slug", "endgame_exercises", ["slug"])
        op.create_index("ix_endgame_exercises_category", "endgame_exercises", ["category"])
        op.create_index("ix_endgame_exercises_difficulty", "endgame_exercises", ["difficulty"])

    if not _has_table("endgame_review_states"):
        op.create_table(
            "endgame_review_states",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("exercise_id", sa.String(36), sa.ForeignKey("endgame_exercises.id", ondelete="CASCADE"), nullable=False),
            sa.Column("repetitions", sa.Integer(), nullable=False),
            sa.Column("interval_days", sa.Integer(), nullable=False),
            sa.Column("ease_factor", sa.Float(), nullable=False),
            sa.Column("lapses", sa.Integer(), nullable=False),
            sa.Column("mastery", sa.Float(), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("user_id", "exercise_id", name="uq_user_endgame_review"),
        )
        op.create_index("ix_endgame_review_states_user_id", "endgame_review_states", ["user_id"])
        op.create_index("ix_endgame_review_states_exercise_id", "endgame_review_states", ["exercise_id"])
        op.create_index("ix_endgame_review_states_due_at", "endgame_review_states", ["due_at"])

    if not _has_table("endgame_attempts"):
        op.create_table(
            "endgame_attempts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("exercise_id", sa.String(36), sa.ForeignKey("endgame_exercises.id", ondelete="CASCADE"), nullable=False),
            sa.Column("move_uci", sa.String(8), nullable=False),
            sa.Column("correct", sa.Boolean(), nullable=False),
            sa.Column("grade", sa.String(16), nullable=False),
            sa.Column("attempted_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_endgame_attempts_user_id", "endgame_attempts", ["user_id"])
        op.create_index("ix_endgame_attempts_exercise_id", "endgame_attempts", ["exercise_id"])
        op.create_index("ix_endgame_attempts_attempted_at", "endgame_attempts", ["attempted_at"])


def downgrade():
    if _has_table("endgame_attempts"):
        op.drop_table("endgame_attempts")
    if _has_table("endgame_review_states"):
        op.drop_table("endgame_review_states")
    if _has_table("endgame_exercises"):
        op.drop_table("endgame_exercises")
