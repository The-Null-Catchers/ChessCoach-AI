"""engine analysis profiles and MultiPV candidates

Revision ID: 0012_engine_profiles
Revises: 0011_feature_flags
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_engine_profiles"
down_revision = "0011_feature_flags"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    position_columns = {column["name"] for column in inspector.get_columns("position_analyses")}
    if "multipv" not in position_columns:
        op.add_column(
            "position_analyses",
            sa.Column("multipv", sa.Integer(), nullable=False, server_default="1"),
        )
    if "candidates_json" not in position_columns:
        op.add_column("position_analyses", sa.Column("candidates_json", sa.Text(), nullable=True))

    constraints = {item["name"] for item in inspector.get_unique_constraints("position_analyses")}
    if "uq_cached_position" in constraints:
        op.drop_constraint("uq_cached_position", "position_analyses", type_="unique")
    op.create_unique_constraint(
        "uq_cached_position",
        "position_analyses",
        ["position_hash", "engine_key", "depth", "multipv"],
    )

    review_columns = {column["name"] for column in inspector.get_columns("review_states")}
    if "mastery" in review_columns:
        op.drop_column("review_states", "mastery")

    engine_columns = {column["name"] for column in inspector.get_columns("engine_analyses")}
    if "analysis_profile" not in engine_columns:
        op.add_column(
            "engine_analyses",
            sa.Column("analysis_profile", sa.String(16), nullable=False, server_default="normal"),
        )
    if "candidate_moves_json" not in engine_columns:
        op.add_column("engine_analyses", sa.Column("candidate_moves_json", sa.Text(), nullable=True))

    review_columns = {column["name"] for column in inspector.get_columns("review_states")}
    if "mastery" not in review_columns:
        op.add_column(
            "review_states",
            sa.Column("mastery", sa.Float(), nullable=False, server_default="0"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    engine_columns = {column["name"] for column in inspector.get_columns("engine_analyses")}
    if "candidate_moves_json" in engine_columns:
        op.drop_column("engine_analyses", "candidate_moves_json")
    if "analysis_profile" in engine_columns:
        op.drop_column("engine_analyses", "analysis_profile")

    position_columns = {column["name"] for column in inspector.get_columns("position_analyses")}
    constraints = {item["name"] for item in inspector.get_unique_constraints("position_analyses")}
    if "uq_cached_position" in constraints:
        op.drop_constraint("uq_cached_position", "position_analyses", type_="unique")
    op.create_unique_constraint(
        "uq_cached_position",
        "position_analyses",
        ["position_hash", "engine_key", "depth"],
    )
    if "candidates_json" in position_columns:
        op.drop_column("position_analyses", "candidates_json")
    if "multipv" in position_columns:
        op.drop_column("position_analyses", "multipv")
