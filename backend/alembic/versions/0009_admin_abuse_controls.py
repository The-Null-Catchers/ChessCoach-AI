"""admin abuse controls

Revision ID: 0009_admin_abuse_controls
Revises: 0008_endgame_trainer
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_admin_abuse_controls"
down_revision = "0008_endgame_trainer"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "is_admin" not in columns:
        op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.create_index("ix_users_is_admin", "users", ["is_admin"])
    if "is_suspended" not in columns:
        op.add_column("users", sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.create_index("ix_users_is_suspended", "users", ["is_suspended"])
    if "suspended_at" not in columns:
        op.add_column("users", sa.Column("suspended_at", sa.DateTime(), nullable=True))
    if "suspension_reason" not in columns:
        op.add_column("users", sa.Column("suspension_reason", sa.String(255), nullable=True))


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "suspension_reason" in columns:
        op.drop_column("users", "suspension_reason")
    if "suspended_at" in columns:
        op.drop_column("users", "suspended_at")
    if "is_suspended" in columns:
        op.drop_index("ix_users_is_suspended", table_name="users")
        op.drop_column("users", "is_suspended")
    if "is_admin" in columns:
        op.drop_index("ix_users_is_admin", table_name="users")
        op.drop_column("users", "is_admin")
