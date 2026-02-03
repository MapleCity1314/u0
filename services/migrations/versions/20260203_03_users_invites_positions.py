from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260203_03"
down_revision = "20260203_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_id", sa.String(length=16), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_display_id", "users", ["display_id"], unique=True)

    op.create_table(
        "invites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invites_owner", "invites", ["owner_id"])
    op.create_index("ix_invites_status", "invites", ["status"])
    op.create_index("ix_invites_expires", "invites", ["expires_at"])
    op.create_index("ix_invites_code", "invites", ["code"], unique=True)

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("units", sa.Float, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("amount", sa.Float, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_positions_user", "positions", ["user_id"])
    op.create_index("ix_positions_code", "positions", ["code"])
    op.create_index("ix_positions_active", "positions", ["is_active"])
    op.create_index(
        "uq_positions_user_code_active",
        "positions",
        ["user_id", "code", "is_active"],
        unique=True,
    )

    op.create_table(
        "position_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("position_id", sa.Integer, sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("delta_units", sa.Float, nullable=True),
        sa.Column("delta_amount", sa.Float, nullable=True),
        sa.Column("delta_cost", sa.Float, nullable=True),
        sa.Column("payload", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_position_events_user", "position_events", ["user_id"])
    op.create_index("ix_position_events_position", "position_events", ["position_id"])
    op.create_index("ix_position_events_type", "position_events", ["event_type"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("resource", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("extra", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_user", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource"])


def downgrade():
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_position_events_type", table_name="position_events")
    op.drop_index("ix_position_events_position", table_name="position_events")
    op.drop_index("ix_position_events_user", table_name="position_events")
    op.drop_table("position_events")

    op.drop_index("uq_positions_user_code_active", table_name="positions")
    op.drop_index("ix_positions_active", table_name="positions")
    op.drop_index("ix_positions_code", table_name="positions")
    op.drop_index("ix_positions_user", table_name="positions")
    op.drop_table("positions")

    op.drop_index("ix_invites_code", table_name="invites")
    op.drop_index("ix_invites_expires", table_name="invites")
    op.drop_index("ix_invites_status", table_name="invites")
    op.drop_index("ix_invites_owner", table_name="invites")
    op.drop_table("invites")

    op.drop_index("ix_users_display_id", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
