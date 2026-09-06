from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from .identity import fingerprint, normalize_text
from .schemas import ProductView


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    canonical_uuid: UUID
    canonical_id: str
    product: ProductView
    aliases: tuple[str, ...]
    identifiers: tuple[str, ...]
    provenance: tuple[dict[str, Any], ...]
    alias_records: tuple[dict[str, str], ...] = ()
    identifier_records: tuple[dict[str, str], ...] = ()

    @property
    def searchable_text(self) -> str:
        p = self.product
        parts = [p.brand, p.casting, p.series, p.color, p.collector_number,
                 p.series_position, p.rarity_tier, p.edition, *self.aliases, *self.identifiers]
        return " ".join(str(value) for value in parts if value not in (None, ""))


class Catalog:
    def __init__(self, version: str, products: list[CatalogProduct]) -> None:
        self.version = version
        self.products = tuple(products)
        self.by_uuid = {product.canonical_uuid: product for product in products}
        self.by_id = {product.canonical_id: product for product in products}


def _alias_text(item: Any) -> str:
    return item if isinstance(item, str) else str(item.get("alias_text", ""))


def _identifier_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    return str(item.get("identifier_value", item.get("normalized_value", "")))


def load_catalog(path: Path) -> Catalog:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
        raise ValueError("catalog must be an object containing products[]")
    version = str(payload.get("catalog_version") or payload.get("dataset_version") or "unknown")
    products: list[CatalogProduct] = []
    uuids: set[UUID] = set()
    slugs: set[str] = set()
    keys: dict[str, str] = {}
    for index, raw in enumerate(payload["products"]):
        try:
            canonical_uuid = UUID(str(raw["canonical_uuid"]))
            canonical_id = str(raw["canonical_id"])
            product = ProductView.model_validate({
                field: raw.get(field) for field in ProductView.model_fields
            })
        except Exception as error:
            raise ValueError(f"invalid catalog product at index {index}: {error}") from error
        if canonical_uuid in uuids or canonical_id in slugs:
            raise ValueError(f"duplicate catalog identity at index {index}")
        key = fingerprint(raw)
        if key in keys and keys[key] != canonical_id:
            raise ValueError(f"natural-key collision: {canonical_id} and {keys[key]}")
        raw_aliases = raw.get("aliases", [])
        raw_identifiers = raw.get("identifiers", [])
        aliases = tuple(value for item in raw_aliases if (value := _alias_text(item)))
        identifiers = tuple(
            value for item in raw_identifiers if (value := _identifier_text(item))
        )
        alias_records = tuple(
            {
                "alias_text": value,
                "alias_type": str(item.get("alias_type") or "catalog_alias"),
                "source_id": str(item.get("source_id") or f"catalog://{canonical_id}"),
            }
            for item in raw_aliases
            if isinstance(item, dict) and (value := _alias_text(item))
        )
        identifier_records = tuple(
            {
                "identifier_type": str(item.get("identifier_type") or "catalog_identifier"),
                "identifier_value": value,
                "source_id": str(item.get("source_id") or f"catalog://{canonical_id}"),
            }
            for item in raw_identifiers
            if isinstance(item, dict) and (value := _identifier_text(item))
        )
        provenance = tuple(raw.get("provenance", []))
        if not provenance:
            raise ValueError(f"product {canonical_id} has no provenance")
        uuids.add(canonical_uuid)
        slugs.add(canonical_id)
        keys[key] = canonical_id
        products.append(CatalogProduct(
            canonical_uuid=canonical_uuid,
            canonical_id=canonical_id,
            product=product,
            aliases=aliases,
            identifiers=identifiers,
            provenance=provenance,
            alias_records=alias_records,
            identifier_records=identifier_records,
        ))
    if not products:
        raise ValueError("catalog contains no products")
    return Catalog(version, products)


def catalog_checksum(catalog: Catalog) -> str:
    def stable(values: Any) -> list[Any]:
        return sorted(
            values,
            key=lambda value: json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )

    rows = [
        {
            "canonical_uuid": str(item.canonical_uuid),
            "canonical_id": item.canonical_id,
            "product": item.product.model_dump(mode="json"),
            "aliases": stable(item.alias_records or list(item.aliases)),
            "identifiers": stable(item.identifier_records or list(item.identifiers)),
            "provenance": stable(item.provenance),
        }
        for item in catalog.products
    ]
    rows.sort(key=lambda row: row["canonical_uuid"])
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_tokens(product: CatalogProduct) -> set[str]:
    return set(normalize_text(product.searchable_text).split())
