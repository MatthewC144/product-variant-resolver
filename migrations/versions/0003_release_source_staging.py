"""Add isolated review-only release source staging.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "release_source_batch",
        sa.Column("batch_id", sa.Text(), primary_key=True),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("import_version", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_rights_state", sa.Text(), nullable=False),
        sa.Column("files", postgresql.JSONB(), nullable=False),
        sa.Column("counts", postgresql.JSONB(), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "schema_version = 'pvr-local-release-staging-v1'", name="ck_release_batch_schema"
        ),
        sa.CheckConstraint(
            "import_version = 'local-xlsx-openpyxl-v1'", name="ck_release_batch_import"
        ),
        sa.CheckConstraint(
            "status = 'review_only_local_staging_snapshot'", name="ck_release_batch_status"
        ),
        sa.CheckConstraint(
            "source_rights_state = 'access_permission_and_republication_rights_not_provided'",
            name="ck_release_batch_rights",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'", name="ck_release_batch_content_hash"
        ),
        sa.CheckConstraint(
            "batch_id = 'local-release-staging-v1-' || content_sha256",
            name="ck_release_batch_identity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(files) = 'array' AND jsonb_array_length(files) = 4",
            name="ck_release_batch_files",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(counts) = 'object' "
            "AND (counts->>'staged_observations')::integer = 1763 "
            "AND (counts->>'unknown_colors')::integer = 1763 "
            "AND (counts->>'canonical_products')::integer = 0",
            name="ck_release_batch_counts",
        ),
    )
    op.create_table(
        "release_source_record",
        sa.Column(
            "batch_id",
            sa.Text(),
            sa.ForeignKey("release_source_batch.batch_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source_record_id", sa.Text(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("toy_number", sa.Text(), nullable=False),
        sa.Column("collector_number", sa.Text(), nullable=False),
        sa.Column("source_model_label", sa.Text(), nullable=False),
        sa.Column("casting_name", sa.Text(), nullable=False),
        sa.Column("variant_note", sa.Text()),
        sa.Column("series", sa.Text(), nullable=False),
        sa.Column("series_position", sa.Text(), nullable=False),
        sa.Column("color", sa.Text()),
        sa.Column("source_page_title", sa.Text(), nullable=False),
        sa.Column("source_page_url", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.Text(), nullable=False),
        sa.Column("parse_error", sa.Text()),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_fields", postgresql.JSONB(), nullable=False),
        sa.Column("input_filename", sa.Text(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("usage", sa.Text(), nullable=False),
        sa.Column("canonical_uuid", postgresql.UUID(as_uuid=True)),
        sa.UniqueConstraint("batch_id", "ordinal", name="uq_release_record_ordinal"),
        sa.UniqueConstraint("batch_id", "toy_number", name="uq_release_record_toy_number"),
        sa.CheckConstraint("ordinal BETWEEN 0 AND 1762", name="ck_release_record_ordinal"),
        sa.CheckConstraint("release_year BETWEEN 2023 AND 2026", name="ck_release_record_year"),
        sa.CheckConstraint("color IS NULL", name="ck_release_record_unknown_color"),
        sa.CheckConstraint(
            "parse_status = 'parsed' AND parse_error IS NULL", name="ck_release_record_parse"
        ),
        sa.CheckConstraint(
            "review_status = 'needs_canonical_review'", name="ck_release_record_review"
        ),
        sa.CheckConstraint(
            "usage = 'staging_only_not_evaluation_or_canonical'", name="ck_release_record_usage"
        ),
        sa.CheckConstraint("canonical_uuid IS NULL", name="ck_release_record_no_canonical"),
        sa.CheckConstraint("input_sha256 ~ '^[0-9a-f]{64}$'", name="ck_release_record_input_hash"),
        sa.CheckConstraint(
            "jsonb_typeof(raw_fields) = 'object'", name="ck_release_record_raw_object"
        ),
    )
    op.create_index("ix_release_source_record_casting", "release_source_record", ["casting_name"])


def downgrade() -> None:
    op.drop_index("ix_release_source_record_casting", table_name="release_source_record")
    op.drop_table("release_source_record")
    op.drop_table("release_source_batch")
