from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from product_variant_resolver.catalog import Catalog, load_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.ingestion import InMemoryCatalogRepository, ingest_catalog
from product_variant_resolver.postgres_ingestion import PostgresCatalogRepository
from product_variant_resolver.service import ResolverService

ROOT = Path(__file__).resolve().parents[2]


def _row(
    number: int,
    *,
    canonical_id: str,
    release_key: str,
    toy_number: str,
) -> dict[str, object]:
    return {
        "canonical_uuid": str(UUID(int=number)),
        "canonical_id": canonical_id,
        "brand": "Hot Wheels",
        "casting": "Repeated Casting",
        "release_year": 2025,
        "series": "Mainline",
        "color": None,
        "collector_number": "001",
        "series_position": "1/10",
        "rarity_tier": None,
        "edition": None,
        "release_key": release_key,
        "aliases": [],
        "identifiers": [
            {
                "identifier_type": "toy_number",
                "identifier_value": toy_number,
                "source_id": f"source://{toy_number}",
            }
        ],
        "provenance": [
            {
                "field_name": None,
                "value_snapshot": toy_number,
                "source_name": "test_source",
                "source_reference": f"source://{toy_number}",
                "retrieved_at": "2026-09-30T00:00:00Z",
                "license_note": "test license",
                "confidence_note": "catalog inclusion is not exact authority",
            }
        ],
    }


def _write_catalog(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"catalog_version": "catalog-v2", "products": rows}),
        encoding="utf-8",
    )


def _duplicate_natural_catalog(tmp_path: Path) -> Catalog:
    path = tmp_path / "catalog.json"
    _write_catalog(
        path,
        [
            _row(
                1,
                canonical_id="repeated-casting-hyx45",
                release_key="release-2025-hyx45",
                toy_number="HYX45",
            ),
            _row(
                2,
                canonical_id="repeated-casting-hyy10",
                release_key="release-2025-hyy10",
                toy_number="HYY10",
            ),
        ],
    )
    return load_catalog(path)


def test_in_memory_ingestion_accepts_release_disambiguated_natural_duplicates(
    tmp_path: Path,
) -> None:
    catalog = _duplicate_natural_catalog(tmp_path)
    repository = InMemoryCatalogRepository()

    ingest_catalog(catalog, repository)
    first = (dict(repository.rows), repository.version, repository.checksum)
    ingest_catalog(catalog, repository)

    assert len(repository.rows) == 2
    assert (repository.rows, repository.version, repository.checksum) == first


def test_resolver_service_loads_release_disambiguated_catalog_v2(tmp_path: Path) -> None:
    catalog = _duplicate_natural_catalog(tmp_path)
    settings = Settings(
        catalog_path=tmp_path / "catalog.json",
        benchmark_path=ROOT / "data/benchmark.json",
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=(ROOT / "data/review_family_knowledge_manifest.json"),
    )

    service = ResolverService.from_settings(settings)

    assert service.catalog.version == "catalog-v2"
    assert service.catalog.products == catalog.products


def test_in_memory_ingestion_preserves_legacy_natural_collision_rejection(
    tmp_path: Path,
) -> None:
    catalog = _duplicate_natural_catalog(tmp_path)
    legacy_collision = Catalog(
        "fixture-v1",
        [replace(product, release_key=None) for product in catalog.products],
    )
    repository = InMemoryCatalogRepository()

    with pytest.raises(ValueError, match="natural key collision"):
        ingest_catalog(legacy_collision, repository)

    assert repository.rows == {}


def test_in_memory_ingestion_rejects_release_and_identifier_collisions(
    tmp_path: Path,
) -> None:
    catalog = _duplicate_natural_catalog(tmp_path)
    first, second = catalog.products
    repository = InMemoryCatalogRepository()
    ingest_catalog(Catalog("first", [first]), repository)
    snapshot = dict(repository.rows)

    with pytest.raises(ValueError, match="release_key collision"):
        ingest_catalog(
            Catalog("release-collision", [first, replace(second, release_key=first.release_key)]),
            repository,
        )
    assert repository.rows == snapshot

    with pytest.raises(ValueError, match="normalized identifier collision"):
        ingest_catalog(
            Catalog(
                "identifier-collision",
                [
                    first,
                    replace(
                        second,
                        identifiers=first.identifiers,
                        identifier_records=first.identifier_records,
                    ),
                ],
            ),
            repository,
        )
    assert repository.rows == snapshot


def test_in_memory_ingestion_rejects_empty_release_and_duplicate_identifiers(
    tmp_path: Path,
) -> None:
    product = _duplicate_natural_catalog(tmp_path).products[0]

    with pytest.raises(ValueError, match="release_key normalizes to an empty string"):
        ingest_catalog(
            Catalog("empty-release", [replace(product, release_key="---")]),
            InMemoryCatalogRepository(),
        )

    with pytest.raises(ValueError, match="duplicate normalized identifier"):
        ingest_catalog(
            Catalog(
                "duplicate-identifier",
                [
                    replace(
                        product,
                        identifier_records=(
                            *product.identifier_records,
                            *product.identifier_records,
                        ),
                    )
                ],
            ),
            InMemoryCatalogRepository(),
        )


class _Result:
    def __init__(self, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self.rows = rows or []
        self.scalar = scalar

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def scalar_one_or_none(self) -> Any:
        return self.scalar

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.rows)


class _PostgresHarness(PostgresCatalogRepository):
    def __init__(self, *, existing_release_key: str | None, has_toy_number: bool) -> None:
        self.engine = None
        self._connection = object()
        self._transaction = None
        self._seen_uuids = set()
        self.statements: list[str] = []
        self.existing_release_key = existing_release_key
        self.has_toy_number = has_toy_number

    def _execute(self, statement: str, parameters: dict[str, Any] | None = None) -> _Result:
        self.statements.append(statement)
        if statement.startswith("SELECT canonical_uuid, canonical_id, release_key"):
            return _Result()
        if "FROM product_variant AS product" in statement:
            return _Result(
                [
                    {
                        "canonical_uuid": "00000000-0000-0000-0000-000000000001",
                        "release_key": self.existing_release_key,
                        "has_toy_number": self.has_toy_number,
                    }
                ]
            )
        if statement.startswith("SELECT canonical_uuid, canonical_id, release_key"):
            return _Result()
        if statement.startswith("SELECT id, alias_text"):
            return _Result()
        if statement.startswith("SELECT id, canonical_uuid, identifier_type"):
            return _Result()
        if statement.startswith("SELECT id, canonical_uuid, identifier_value"):
            return _Result()
        if statement.startswith("SELECT field_name"):
            return _Result()
        if statement.startswith("SELECT search_text"):
            return _Result(scalar=None)
        return _Result()


def test_postgres_ingestion_persists_release_key_and_locks_natural_identity(
    tmp_path: Path,
) -> None:
    product = _duplicate_natural_catalog(tmp_path).products[1]
    repository = _PostgresHarness(existing_release_key="release-2025-hyx45", has_toy_number=True)

    repository.upsert(product)

    statements = "\n".join(repository.statements)
    assert "pg_advisory_xact_lock" in statements
    assert "INSERT INTO product_variant" in statements
    assert "release_key" in statements
    assert "normalized_release_key" in statements


@pytest.mark.parametrize(
    ("release_key", "has_toy_number"), [(None, True), ("release-2025-hyx45", False)]
)
def test_postgres_ingestion_rejects_undisambiguated_natural_rows(
    tmp_path: Path, release_key: str | None, has_toy_number: bool
) -> None:
    product = _duplicate_natural_catalog(tmp_path).products[1]
    repository = _PostgresHarness(existing_release_key=release_key, has_toy_number=has_toy_number)

    with pytest.raises(ValueError, match="natural key collision"):
        repository.upsert(product)

    assert not any(
        statement.startswith("INSERT INTO product_variant") for statement in repository.statements
    )


def test_catalog_release_identity_migration_contract() -> None:
    path = (
        Path(__file__).resolve().parents[2] / "migrations/versions/0004_catalog_release_identity.py"
    )
    spec = importlib.util.spec_from_file_location("catalog_release_identity_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0004"
    assert module.down_revision == "0003"
    source = path.read_text(encoding="utf-8")
    assert 'sa.Column("release_key", sa.String(300), nullable=True)' in source
    assert 'sa.Column("normalized_release_key", sa.String(300), nullable=True)' in source
    assert '"uq_product_variant_normalized_release_key"' in source
    assert '"product_variant_natural_key_fingerprint_key"' in source
    assert '"ix_product_variant_natural_key_fingerprint"' in source
