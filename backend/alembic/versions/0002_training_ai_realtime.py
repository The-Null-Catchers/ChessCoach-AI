"""training, spaced repetition, and AI coaching tables

Revision ID: 0002_training_ai_realtime
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_training_ai_realtime"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if not _has_table("review_states"):
        op.create_table(
            "review_states",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("puzzle_id", sa.String(36), sa.ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
            sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("user_id", "puzzle_id", name="uq_user_puzzle_review"),
        )
        op.create_index("ix_review_states_user_id", "review_states", ["user_id"])
        op.create_index("ix_review_states_puzzle_id", "review_states", ["puzzle_id"])
        op.create_index("ix_review_states_due_at", "review_states", ["due_at"])

    if not _has_table("training_plans"):
        op.create_table(
            "training_plans",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("week_start", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="active"),
            sa.Column("focus_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "week_start", name="uq_user_training_week"),
        )
        op.create_index("ix_training_plans_user_id", "training_plans", ["user_id"])
        op.create_index("ix_training_plans_week_start", "training_plans", ["week_start"])

    if not _has_table("training_sessions"):
        op.create_table(
            "training_sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("plan_id", sa.String(36), sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_type", sa.String(40), nullable=False),
            sa.Column("focus_category", sa.String(80), nullable=True),
            sa.Column("target_count", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("scheduled_for", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("minutes_spent", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_training_sessions_plan_id", "training_sessions", ["plan_id"])
        op.create_index("ix_training_sessions_user_id", "training_sessions", ["user_id"])
        op.create_index("ix_training_sessions_session_type", "training_sessions", ["session_type"])
        op.create_index("ix_training_sessions_scheduled_for", "training_sessions", ["scheduled_for"])

    if not _has_table("ai_explanations"):
        op.create_table(
            "ai_explanations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("move_id", sa.String(36), sa.ForeignKey("moves.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("model", sa.String(80), nullable=False),
            sa.Column("prompt_version", sa.String(32), nullable=False),
            sa.Column("skill_band", sa.String(24), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("coaching_tip", sa.Text(), nullable=False),
            sa.Column("structured_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("move_id", "prompt_version", "skill_band", name="uq_move_ai_explanation"),
        )
        op.create_index("ix_ai_explanations_move_id", "ai_explanations", ["move_id"])

    if not _has_table("player_insights"):
        op.create_table(
            "player_insights",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("insight_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_player_insights_user_id", "player_insights", ["user_id"])
        op.create_index("ix_player_insights_insight_type", "player_insights", ["insight_type"])
        op.create_index("ix_player_insights_created_at", "player_insights", ["created_at"])


def downgrade():
    for name in ["player_insights", "ai_explanations", "training_sessions", "training_plans", "review_states"]:
        if _has_table(name):
            op.drop_table(name)
