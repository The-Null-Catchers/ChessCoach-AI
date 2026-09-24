"""auth action tokens

Revision ID: 0006_auth_action_tokens
Revises: 0005_auth_sessions_audit
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_auth_action_tokens"
down_revision = "0005_auth_sessions_audit"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if _has_table("auth_action_tokens"):
        return

    op.create_table(
        "auth_action_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_auth_action_token_hash"),
    )
    op.create_index("ix_auth_action_tokens_user_id", "auth_action_tokens", ["user_id"])
    op.create_index("ix_auth_action_tokens_purpose", "auth_action_tokens", ["purpose"])
    op.create_index("ix_auth_action_tokens_token_hash", "auth_action_tokens", ["token_hash"])
    op.create_index("ix_auth_action_tokens_expires_at", "auth_action_tokens", ["expires_at"])


def downgrade():
    if _has_table("auth_action_tokens"):
        op.drop_table("auth_action_tokens")
