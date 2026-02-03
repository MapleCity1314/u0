from alembic import op
import sqlalchemy as sa

revision = "20260203_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("tags", sa.String(length=256), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_news_items_published", "news_items", ["published_at"])
    op.create_index("ix_news_items_source", "news_items", ["source"])
    op.create_index("ix_news_items_market", "news_items", ["market"])
    op.create_index("ix_news_items_title", "news_items", ["title"])

    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("extra", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("log_entries")
    op.drop_index("ix_news_items_title", table_name="news_items")
    op.drop_index("ix_news_items_market", table_name="news_items")
    op.drop_index("ix_news_items_source", table_name="news_items")
    op.drop_index("ix_news_items_published", table_name="news_items")
    op.drop_table("news_items")
