from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from .catalog import Catalog, CatalogProduct, catalog_checksum
from .identity import fingerprint, normalize_text


def _identifier_keys(product: CatalogProduct) -> set[tuple[str, str]]:
    records = product.identifier_records or tuple(
        {
            "identifier_type": "catalog_identifier",
            "identifier_value": value,
        }
        for value in product.identifiers
    )
    keys = [
        (
            normalize_text(record["identifier_type"]),
            normalize_text(record["identifier_value"]),
        )
        for record in records
    ]
    if any(not identifier_type or not value for identifier_type, value in keys):
        raise ValueError("catalog identifier normalizes to an empty string")
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate normalized identifier within one product")
    return set(keys)


def _normalized_release_key(product: CatalogProduct) -> str | None:
    if product.release_key is None:
        return None
    normalized = normalize_text(product.release_key)
    if not normalized:
        raise ValueError("release_key normalizes to an empty string")
    return normalized


def _has_toy_number(product: CatalogProduct) -> bool:
    return any(identifier_type == "toy_number" for identifier_type, _ in _identifier_keys(product))


def _natural_collision_is_disambiguated(first: CatalogProduct, second: CatalogProduct) -> bool:
    return (
        _normalized_release_key(first) is not None
        and _normalized_release_key(second) is not None
        and _normalized_release_key(first) != _normalized_release_key(second)
        and _has_toy_number(first)
        and _has_toy_number(second)
    )


class CatalogRepository(Protocol):
    def begin(self) -> None: ...
    def upsert(self, product: CatalogProduct) -> None: ...
    def set_version(self, version: str, checksum: str) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


def ingest_catalog(catalog: Catalog, repository: CatalogRepository) -> None:
    """Idempotent orchestration. Repository implementations own the database transaction."""
    repository.begin()
    try:
        for product in catalog.products:
            repository.upsert(product)
        repository.set_version(catalog.version, catalog_checksum(catalog))
        repository.commit()
    except Exception:
        repository.rollback()
        raise


@dataclass(slots=True)
class InMemoryCatalogRepository:
    """Transactional test/offline repository; PostgreSQL implementation uses the same contract."""

    rows: dict[UUID, CatalogProduct] = field(default_factory=dict)
    version: str | None = None
    checksum: str | None = None
    _snapshot: tuple[dict[UUID, CatalogProduct], str | None, str | None] | None = None

    def begin(self) -> None:
        if self._snapshot is not None:
            raise RuntimeError("transaction already active")
        self._snapshot = (dict(self.rows), self.version, self.checksum)

    def upsert(self, product: CatalogProduct) -> None:
        existing = self.rows.get(product.canonical_uuid)
        if existing and existing.canonical_id != product.canonical_id:
            raise ValueError("immutable canonical_id changed")
        if existing and existing.release_key != product.release_key:
            raise ValueError("immutable release_key changed")
        normalized_release_key = _normalized_release_key(product)
        product_identifier_keys = _identifier_keys(product)
        for uuid_, row in self.rows.items():
            if row.canonical_id == product.canonical_id and uuid_ != product.canonical_uuid:
                raise ValueError("canonical_id collision")
            if (
                _normalized_release_key(row) is not None
                and normalized_release_key is not None
                and _normalized_release_key(row) == normalized_release_key
                and uuid_ != product.canonical_uuid
            ):
                raise ValueError("release_key collision")
            if uuid_ != product.canonical_uuid and _identifier_keys(row) & product_identifier_keys:
                raise ValueError("normalized identifier collision")
            if (
                fingerprint(row.product.model_dump()) == fingerprint(product.product.model_dump())
                and uuid_ != product.canonical_uuid
                and not _natural_collision_is_disambiguated(row, product)
            ):
                raise ValueError("natural key collision")
        self.rows[product.canonical_uuid] = product

    def set_version(self, version: str, checksum: str) -> None:
        self.version, self.checksum = version, checksum

    def commit(self) -> None:
        if self._snapshot is None:
            raise RuntimeError("no transaction")
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            self.rows, self.version, self.checksum = self._snapshot
            self._snapshot = None
