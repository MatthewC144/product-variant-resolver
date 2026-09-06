"""Run the T04 PostgreSQL migration cycle and assert the resulting schema.

This runner intentionally requires an empty application schema. Run it against an
isolated database/Compose project so it cannot downgrade a developer database.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.pool import NullPool


APPLICATION_TABLES = {
    "identifier",
    "index_metadata",
    "product_alias",
    "product_embedding",
    "product_search",
    "product_variant",
    "provenance_record",
}
EXPECTED_INDEXES = {
    ("product_variant", "ix_product_variant_casting", "btree", ("casting",)),
    ("product_alias", "ix_product_alias_normalized", "btree", ("normalized_alias",)),
    ("identifier", "ix_identifier_product", "btree", ("canonical_uuid",)),
    ("provenance_record", "ix_provenance_product", "btree", ("canonical_uuid",)),
    ("product_search", "ix_product_search_document", "gin", ("search_document",)),
}
EXPECTED_FOREIGN_KEYS = {
    ("product_alias", ("canonical_uuid",), "product_variant", ("canonical_uuid",), "CASCADE"),
    ("identifier", ("canonical_uuid",), "product_variant", ("canonical_uuid",), "CASCADE"),
    (
        "provenance_record",
        ("canonical_uuid",),
        "product_variant",
        ("canonical_uuid",),
        "CASCADE",
    ),
    ("product_search", ("canonical_uuid",), "product_variant", ("canonical_uuid",), "CASCADE"),
    (
        "product_embedding",
        ("canonical_uuid",),
        "product_variant",
        ("canonical_uuid",),
        "CASCADE",
    ),
}
EXPECTED_RELEASE_YEAR_CHECKS = {
    "release_yearisnullorrelease_yearbetween1960and2050",
    "release_yearisnullorrelease_year>=1960andrelease_year<=2050",
}


def _database_url() -> str:
    value = os.getenv("PVR_DATABASE_URL")
    if not value:
        raise RuntimeError("PVR_DATABASE_URL is required")
    return value


def _alembic_config(database_url: str) -> Config:
    repository_root = Path(__file__).resolve().parents[1]
    config_path = repository_root / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(repository_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _application_tables(connection: sa.Connection) -> set[str]:
    rows = connection.execute(
        sa.text(
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
    )
    return {row[0] for row in rows}


def _assert_empty(engine: sa.Engine) -> None:
    with engine.connect() as connection:
        tables = _application_tables(connection)
    if tables:
        raise AssertionError(
            "migration verification requires an empty application schema; found: "
            + ", ".join(sorted(tables))
        )


def _normalize_check_expression(expression: str) -> str:
    normalized = re.sub(r"\s+", "", expression.lower())
    return normalized.replace("(", "").replace(")", "")


def _schema_snapshot(engine: sa.Engine) -> dict[str, Any]:
    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names(schema="public"))
    assert APPLICATION_TABLES <= tables, sorted(APPLICATION_TABLES - tables)

    primary_keys = {
        table: tuple(inspector.get_pk_constraint(table)["constrained_columns"])
        for table in APPLICATION_TABLES
    }
    assert primary_keys == {
        "identifier": ("id",),
        "index_metadata": ("index_name",),
        "product_alias": ("id",),
        "product_embedding": ("canonical_uuid",),
        "product_search": ("canonical_uuid",),
        "product_variant": ("canonical_uuid",),
        "provenance_record": ("id",),
    }

    product_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("product_variant")
    }
    assert ("canonical_id",) in product_uniques
    assert ("natural_key_fingerprint",) in product_uniques

    alias_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("product_alias")
    }
    assert ("canonical_uuid", "normalized_alias") in alias_uniques

    identifier_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("identifier")
    }
    assert ("identifier_type", "normalized_value") in identifier_uniques

    foreign_keys: set[tuple[str, tuple[str, ...], str, tuple[str, ...], str]] = set()
    for table in APPLICATION_TABLES:
        for foreign_key in inspector.get_foreign_keys(table):
            foreign_keys.add(
                (
                    table,
                    tuple(foreign_key["constrained_columns"]),
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                    foreign_key.get("options", {}).get("ondelete", "").upper(),
                )
            )
    assert EXPECTED_FOREIGN_KEYS <= foreign_keys

    release_year_checks = {
        item["name"]: _normalize_check_expression(item["sqltext"])
        for item in inspector.get_check_constraints("product_variant")
    }
    assert "ck_release_year" in release_year_checks
    assert release_year_checks["ck_release_year"] in EXPECTED_RELEASE_YEAR_CHECKS

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        extension = connection.scalar(
            sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        type_rows = connection.execute(
            sa.text(
                "SELECT c.relname, a.attname, "
                "pg_catalog.format_type(a.atttypid, a.atttypmod) "
                "FROM pg_catalog.pg_attribute a "
                "JOIN pg_catalog.pg_class c ON c.oid = a.attrelid "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped "
                "AND (c.relname, a.attname) IN "
                "(('product_search', 'search_document'), "
                " ('product_embedding', 'embedding'))"
            )
        )
        special_types = {(row[0], row[1]): row[2] for row in type_rows}
        index_rows = connection.execute(
            sa.text(
                "SELECT table_class.relname, index_class.relname, access_method.amname, "
                "array_agg(attribute.attname ORDER BY key.ordinality) "
                "FROM pg_catalog.pg_index index_info "
                "JOIN pg_catalog.pg_class index_class ON index_class.oid = index_info.indexrelid "
                "JOIN pg_catalog.pg_class table_class ON table_class.oid = index_info.indrelid "
                "JOIN pg_catalog.pg_namespace namespace "
                "ON namespace.oid = table_class.relnamespace "
                "JOIN pg_catalog.pg_am access_method ON access_method.oid = index_class.relam "
                "CROSS JOIN LATERAL unnest(index_info.indkey) WITH ORDINALITY "
                "AS key(attribute_number, ordinality) "
                "JOIN pg_catalog.pg_attribute attribute "
                "ON attribute.attrelid = table_class.oid "
                "AND attribute.attnum = key.attribute_number "
                "WHERE namespace.nspname = 'public' "
                "GROUP BY table_class.relname, index_class.relname, access_method.amname"
            )
        )
        indexes = {(row[0], row[1], row[2], tuple(row[3])) for row in index_rows}

    assert revision == "0001"
    assert extension == "vector"
    assert special_types[("product_search", "search_document")] == "tsvector"
    assert special_types[("product_embedding", "embedding")] == "vector(192)"
    assert EXPECTED_INDEXES <= indexes

    return {
        "revision": revision,
        "tables": sorted(APPLICATION_TABLES),
        "extension": extension,
        "special_types": {
            f"{table}.{column}": value
            for (table, column), value in sorted(special_types.items())
        },
        "release_year_check": release_year_checks["ck_release_year"],
        "verified_indexes": [
            {"table": table, "name": index, "method": method, "columns": columns}
            for table, index, method, columns in sorted(EXPECTED_INDEXES)
        ],
        "verified_foreign_keys": [
            {
                "source": f"{table}.{','.join(source_columns)}",
                "target": f"{target_table}.{','.join(target_columns)}",
                "ondelete": ondelete,
            }
            for table, source_columns, target_table, target_columns, ondelete in sorted(
                EXPECTED_FOREIGN_KEYS
            )
        ],
    }


def main() -> None:
    database_url = _database_url()
    engine = sa.create_engine(database_url, poolclass=NullPool)
    config = _alembic_config(database_url)

    _assert_empty(engine)
    command.upgrade(config, "head")
    first_snapshot = _schema_snapshot(engine)

    command.downgrade(config, "base")
    with engine.connect() as connection:
        remaining = _application_tables(connection)
    assert not remaining, sorted(remaining)

    command.upgrade(config, "head")
    final_snapshot = _schema_snapshot(engine)
    assert final_snapshot == first_snapshot

    print(
        json.dumps(
            {
                "status": "passed",
                "cycle": ["empty", "upgrade:0001", "downgrade:base", "upgrade:0001"],
                "schema": final_snapshot,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
