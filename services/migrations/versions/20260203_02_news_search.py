from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260203_02"
down_revision = "20260203_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("news_items", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.add_column("news_items", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True))
    op.create_index("ix_news_items_fingerprint", "news_items", ["fingerprint"], unique=True)
    op.create_index(
        "ix_news_items_search_vector",
        "news_items",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.execute(
        "UPDATE news_items SET "
        "search_vector = to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(summary,'')), "
        "fingerprint = md5(coalesce(title,'') || '|' || coalesce(url,'') || '|' || coalesce(published_at::text,''))"
    )
    op.alter_column("news_items", "fingerprint", nullable=False)


def downgrade():
    op.drop_index("ix_news_items_search_vector", table_name="news_items")
    op.drop_index("ix_news_items_fingerprint", table_name="news_items")
    op.drop_column("news_items", "search_vector")
    op.drop_column("news_items", "fingerprint")
