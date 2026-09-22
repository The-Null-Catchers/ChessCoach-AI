"""refresh sessions and audit logs

Revision ID: 0005_auth_sessions_audit
Revises: 0004_mistake_taxonomy
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_auth_sessions_audit"
down_revision = "0004_mistake_taxonomy"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade():
    if not _has_table("refresh_sessions"):
        op.create_table(
            "refresh_sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_id", sa.String(36), nullable=False),
            sa.Column("jti_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_id", sa.String(36), sa.ForeignKey("refresh_sessions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("jti_hash", name="uq_refresh_session_jti_hash"),
        )
        op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
        op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])
        op.create_index("ix_refresh_sessions_jti_hash", "refresh_sessions", ["jti_hash"])
        op.create_index("ix_refresh_sessions_expires_at", "refresh_sessions", ["expires_at"])

    if not _has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.String(80), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade():
    if _has_table("audit_logs"):
        op.drop_table("audit_logs")
    if _has_table("refresh_sessions"):
        op.drop_table("refresh_sessions")
