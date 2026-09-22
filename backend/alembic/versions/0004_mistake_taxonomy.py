"""normalized mistake taxonomy

Revision ID: 0004_mistake_taxonomy
Revises: 0003_player_analytics
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_mistake_taxonomy"
down_revision = "0003_player_analytics"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if not _has_table("mistake_categories"):
        op.create_table(
            "mistake_categories",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("title", sa.String(120), nullable=False),
            sa.Column("group", sa.String(40), nullable=False),
            sa.UniqueConstraint("slug", name="uq_mistake_category_slug"),
        )
        op.create_index("ix_mistake_categories_slug", "mistake_categories", ["slug"])
        op.create_index("ix_mistake_categories_group", "mistake_categories", ["group"])

    if not _has_table("mistake_category_links"):
        op.create_table(
            "mistake_category_links",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("mistake_id", sa.String(36), sa.ForeignKey("mistakes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category_id", sa.String(36), sa.ForeignKey("mistake_categories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=True),
            sa.UniqueConstraint("mistake_id", "category_id", name="uq_mistake_category_link"),
        )
        op.create_index("ix_mistake_category_links_mistake_id", "mistake_category_links", ["mistake_id"])
        op.create_index("ix_mistake_category_links_category_id", "mistake_category_links", ["category_id"])


def downgrade():
    if _has_table("mistake_category_links"):
        op.drop_table("mistake_category_links")
    if _has_table("mistake_categories"):
        op.drop_table("mistake_categories")
