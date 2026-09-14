"""Add independent human knowledge snapshot storage; never alter canonical0001.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hk_snapshot",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("storage_version", sa.Text(), nullable=False),
        sa.Column("persistence_namespace", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("provisional_variant_count", sa.Integer(), nullable=False),
        sa.Column("review_family_count", sa.Integer(), nullable=False),
        sa.Column("plan_header", postgresql.JSONB(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("storage_version = 'human-knowledge-postgres-storage-v1'",
                           name="ck_hk_storage_version"),
        sa.CheckConstraint("persistence_namespace = 'human-knowledge-isolated-storage-test-v1'",
                           name="ck_hk_namespace"),
        sa.CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="ck_hk_content_hash"),
        sa.CheckConstraint("snapshot_id = 'human-knowledge-plan-v1-' || content_sha256",
                           name="ck_hk_snapshot_identity"),
        sa.CheckConstraint("document_count = 142 AND provisional_variant_count = 100 "
                           "AND review_family_count = 42", name="ck_hk_counts"),
        sa.CheckConstraint("jsonb_typeof(plan_header) = 'object'", name="ck_hk_header_object"),
    )
    op.create_table(
        "hk_document",
        sa.Column("snapshot_id", sa.Text(), sa.ForeignKey("hk_snapshot.snapshot_id"),
                  primary_key=True),
        sa.Column("knowledge_uuid", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_id", sa.Text(), nullable=False),
        sa.Column("knowledge_type", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("origin", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "knowledge_id", name="uq_hk_document_id"),
        sa.UniqueConstraint("snapshot_id", "ordinal", name="uq_hk_document_ordinal"),
        sa.CheckConstraint("knowledge_type IN ('provisional_variant', 'review_family')",
                           name="ck_hk_document_type"),
        sa.CheckConstraint("ordinal BETWEEN 0 AND 141", name="ck_hk_document_ordinal"),
        sa.CheckConstraint("length(knowledge_id) > 0", name="ck_hk_document_id"),
        sa.CheckConstraint("payload_sha256 ~ '^[0-9a-f]{64}$'", name="ck_hk_payload_hash"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object' AND jsonb_typeof(origin) = 'object'",
                           name="ck_hk_document_objects"),
    )


def downgrade() -> None:
    # Only the two new tables; no cascading drop/deletion of canonical tables or extensions.
    op.drop_table("hk_document")
    op.drop_table("hk_snapshot")
