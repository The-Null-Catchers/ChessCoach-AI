"""push notification subscriptions and delivery outbox

Revision ID: 0014_push_notifications
Revises: 0013_weakness_snapshots
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_push_notifications"
down_revision = "0013_weakness_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "push_subscriptions" not in tables:
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("provider", sa.String(32), nullable=False, server_default="default"),
            sa.Column("platform", sa.String(16), nullable=False),
            sa.Column("device_id", sa.String(128), nullable=True),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("token", sa.Text(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
        op.create_index("ix_push_subscriptions_provider", "push_subscriptions", ["provider"])
        op.create_index("ix_push_subscriptions_platform", "push_subscriptions", ["platform"])
        op.create_index("ix_push_subscriptions_token_hash", "push_subscriptions", ["token_hash"], unique=True)
        op.create_index("ix_push_subscriptions_active", "push_subscriptions", ["active"])

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "push_deliveries" not in tables:
        op.create_table(
            "push_deliveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "notification_id",
                sa.String(36),
                sa.ForeignKey("notifications.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "subscription_id",
                sa.String(36),
                sa.ForeignKey("push_subscriptions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("provider_message_id", sa.String(160), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "notification_id",
                "subscription_id",
                name="uq_push_delivery_notification_subscription",
            ),
        )
        op.create_index("ix_push_deliveries_notification_id", "push_deliveries", ["notification_id"])
        op.create_index("ix_push_deliveries_subscription_id", "push_deliveries", ["subscription_id"])
        op.create_index("ix_push_deliveries_status", "push_deliveries", ["status"])
        op.create_index("ix_push_deliveries_created_at", "push_deliveries", ["created_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "push_deliveries" in tables:
        op.drop_table("push_deliveries")
    inspector = sa.inspect(bind)
    if "push_subscriptions" in set(inspector.get_table_names()):
        op.drop_table("push_subscriptions")
