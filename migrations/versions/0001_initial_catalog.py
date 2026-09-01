"""Initial catalog and exact-retrieval schema.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


class Vector192(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):  # type: ignore[no-untyped-def]
        return "vector(192)"

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "product_variant",
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_id", sa.String(300), nullable=False, unique=True),
        sa.Column("natural_key_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("casting", sa.String(200), nullable=False),
        sa.Column("release_year", sa.Integer()),
        sa.Column("series", sa.String(200)),
        sa.Column("color", sa.String(100)),
        sa.Column("collector_number", sa.String(50)),
        sa.Column("series_position", sa.String(50)),
        sa.Column("rarity_tier", sa.String(100)),
        sa.Column("edition", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("release_year IS NULL OR release_year BETWEEN 1960 AND 2050", name="ck_release_year"),
    )
    op.create_index("ix_product_variant_casting", "product_variant", ["casting"])
    op.create_table(
        "product_alias",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variant.canonical_uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.Text(), nullable=False),
        sa.Column("normalized_alias", sa.Text(), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("canonical_uuid", "normalized_alias", name="uq_alias_product_normalized"),
    )
    op.create_index("ix_product_alias_normalized", "product_alias", ["normalized_alias"])
    op.create_table(
        "identifier",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variant.canonical_uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_type", sa.String(80), nullable=False),
        sa.Column("identifier_value", sa.String(300), nullable=False),
        sa.Column("normalized_value", sa.String(300), nullable=False),
        sa.Column("source_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("identifier_type", "normalized_value", name="uq_identifier_type_value"),
    )
    op.create_index("ix_identifier_product", "identifier", ["canonical_uuid"])
    op.create_table(
        "provenance_record",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variant.canonical_uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(100)),
        sa.Column("value_snapshot", sa.Text()),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.Column("confidence_note", sa.Text(), nullable=False),
    )
    op.create_index("ix_provenance_product", "provenance_record", ["canonical_uuid"])
    op.create_table(
        "index_metadata",
        sa.Column("index_name", sa.String(100), primary_key=True),
        sa.Column("catalog_version", sa.String(100), nullable=False),
        sa.Column("artifact_version", sa.String(200), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "product_search",
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variant.canonical_uuid", ondelete="CASCADE"), primary_key=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("search_document", postgresql.TSVECTOR(), nullable=False),
    )
    op.create_index("ix_product_search_document", "product_search", ["search_document"], postgresql_using="gin")
    op.create_table(
        "product_embedding",
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variant.canonical_uuid", ondelete="CASCADE"), primary_key=True),
        sa.Column("embedding_version", sa.String(200), nullable=False),
        sa.Column("embedding", Vector192(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("product_embedding")
    op.drop_index("ix_product_search_document", table_name="product_search")
    op.drop_table("product_search")
    op.drop_table("index_metadata")
    op.drop_index("ix_provenance_product", table_name="provenance_record")
    op.drop_table("provenance_record")
    op.drop_index("ix_identifier_product", table_name="identifier")
    op.drop_table("identifier")
    op.drop_index("ix_product_alias_normalized", table_name="product_alias")
    op.drop_table("product_alias")
    op.drop_index("ix_product_variant_casting", table_name="product_variant")
    op.drop_table("product_variant")
