from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260205_05"
down_revision = "20260203_04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_watchlist_user", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_code", "watchlist_items", ["code"])
    op.create_index("ix_watchlist_active", "watchlist_items", ["is_active"])
    op.create_index(
        "uq_watchlist_user_code_active",
        "watchlist_items",
        ["user_id", "code", "is_active"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_watchlist_user_code_active", table_name="watchlist_items")
    op.drop_index("ix_watchlist_active", table_name="watchlist_items")
    op.drop_index("ix_watchlist_code", table_name="watchlist_items")
    op.drop_index("ix_watchlist_user", table_name="watchlist_items")
    op.drop_table("watchlist_items")
