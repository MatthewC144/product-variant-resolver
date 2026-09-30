"""Persist catalog release identity and permit explicitly disambiguated natural keys.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_variant", sa.Column("release_key", sa.String(300), nullable=True))
    op.add_column(
        "product_variant", sa.Column("normalized_release_key", sa.String(300), nullable=True)
    )
    op.create_unique_constraint(
        "uq_product_variant_normalized_release_key",
        "product_variant",
        ["normalized_release_key"],
    )
    op.create_check_constraint(
        "ck_product_variant_release_key_pair",
        "product_variant",
        "(release_key IS NULL) = (normalized_release_key IS NULL)",
    )
    op.drop_constraint(
        "product_variant_natural_key_fingerprint_key",
        "product_variant",
        type_="unique",
    )
    op.create_index(
        "ix_product_variant_natural_key_fingerprint",
        "product_variant",
        ["natural_key_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_variant_natural_key_fingerprint", table_name="product_variant")
    op.create_unique_constraint(
        "product_variant_natural_key_fingerprint_key",
        "product_variant",
        ["natural_key_fingerprint"],
    )
    op.drop_constraint("ck_product_variant_release_key_pair", "product_variant", type_="check")
    op.drop_constraint(
        "uq_product_variant_normalized_release_key", "product_variant", type_="unique"
    )
    op.drop_column("product_variant", "normalized_release_key")
    op.drop_column("product_variant", "release_key")
