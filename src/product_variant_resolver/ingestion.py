from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from .catalog import Catalog, CatalogProduct, catalog_checksum
from .identity import fingerprint


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
        for uuid_, row in self.rows.items():
            if row.canonical_id == product.canonical_id and uuid_ != product.canonical_uuid:
                raise ValueError("canonical_id collision")
            if fingerprint(row.product.model_dump()) == fingerprint(product.product.model_dump()) and uuid_ != product.canonical_uuid:
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

