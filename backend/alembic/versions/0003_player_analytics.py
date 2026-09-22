"""player identity and analytics tables

Revision ID: 0003_player_analytics
Revises: 0002_training_ai_realtime
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_player_analytics"
down_revision = "0002_training_ai_realtime"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {item["name"] for item in _inspector().get_columns(table)}


def upgrade():
    if not _has_column("games", "variation"):
        op.add_column("games", sa.Column("variation", sa.String(255), nullable=True))
    if not _has_column("games", "time_control"):
        op.add_column("games", sa.Column("time_control", sa.String(64), nullable=True))

    if not _has_table("game_players"):
        op.create_table(
            "game_players",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("game_id", sa.String(36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("color", sa.String(5), nullable=False),
            sa.Column("name", sa.String(120), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.UniqueConstraint("game_id", "color", name="uq_game_player_color"),
        )
        op.create_index("ix_game_players_game_id", "game_players", ["game_id"])
        op.create_index("ix_game_players_user_id", "game_players", ["user_id"])

    if not _has_table("opening_stats"):
        op.create_table(
            "opening_stats",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("eco", sa.String(8), nullable=True),
            sa.Column("opening", sa.String(255), nullable=False),
            sa.Column("variation", sa.String(255), nullable=True),
            sa.Column("color", sa.String(5), nullable=False),
            sa.Column("games_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_accuracy", sa.Float(), nullable=False, server_default="0"),
            sa.Column("common_deviation_ply", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "eco", "opening", "variation", "color", name="uq_user_opening_stat"),
        )
        op.create_index("ix_opening_stats_user_id", "opening_stats", ["user_id"])

    if not _has_table("endgame_stats"):
        op.create_table(
            "endgame_stats",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category", sa.String(64), nullable=False),
            sa.Column("games_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_accuracy", sa.Float(), nullable=False, server_default="0"),
            sa.Column("mistakes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "category", name="uq_user_endgame_stat"),
        )
        op.create_index("ix_endgame_stats_user_id", "endgame_stats", ["user_id"])


def downgrade():
    for name in ["endgame_stats", "opening_stats", "game_players"]:
        if _has_table(name):
            op.drop_table(name)
    if _has_column("games", "time_control"):
        op.drop_column("games", "time_control")
    if _has_column("games", "variation"):
        op.drop_column("games", "variation")
