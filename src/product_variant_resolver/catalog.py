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
    release_key: str | None = None

    @property
    def searchable_text(self) -> str:
        p = self.product
        parts = [
            p.brand,
            p.casting,
            p.series,
            p.color,
            p.collector_number,
            p.series_position,
            p.rarity_tier,
            p.edition,
            *self.aliases,
            *self.identifiers,
        ]
        return " ".join(str(value) for value in parts if value not in (None, ""))


class Catalog:
    def __init__(self, version: str, products: list[CatalogProduct]) -> None:
        self.version = version
        self.products = tuple(products)
        self.by_uuid = {product.canonical_uuid: product for product in products}
        self.by_id = {product.canonical_id: product for product in products}
        self.by_release_key = {
            product.release_key: product for product in products if product.release_key is not None
        }


def _alias_text(item: Any) -> str:
    return item if isinstance(item, str) else str(item.get("alias_text", ""))


def _identifier_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    return str(item.get("identifier_value", item.get("normalized_value", "")))


def _release_key(raw: dict[str, Any], *, index: int) -> str | None:
    value = raw.get("release_key")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid release_key at index {index}")
    if not normalize_text(value):
        raise ValueError(f"release_key normalizes to empty at index {index}")
    return value


def _typed_identifier_key(item: Any, *, index: int) -> tuple[str, str]:
    identifier_type: str
    identifier_value: str
    if isinstance(item, str):
        identifier_type = "catalog_identifier"
        identifier_value = item
    elif isinstance(item, dict):
        raw_identifier_type = item.get("identifier_type")
        raw_identifier_value = item.get("identifier_value", item.get("normalized_value"))
        if not isinstance(raw_identifier_type, str) or not raw_identifier_type.strip():
            raise ValueError(f"invalid identifier_type at index {index}")
        if not isinstance(raw_identifier_value, str) or not raw_identifier_value.strip():
            raise ValueError(f"invalid identifier_value at index {index}")
        identifier_type = raw_identifier_type
        identifier_value = raw_identifier_value
    else:
        raise ValueError(f"invalid identifier at index {index}")  # noqa: TRY004
    normalized_type = normalize_text(identifier_type)
    normalized_value = normalize_text(identifier_value)
    if not normalized_type or not normalized_value:
        raise ValueError(f"identifier normalizes to empty at index {index}")
    return normalized_type, normalized_value


def load_catalog(path: Path) -> Catalog:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
        raise ValueError("catalog must be an object containing products[]")  # noqa: TRY004
    version = str(payload.get("catalog_version") or payload.get("dataset_version") or "unknown")
    products: list[CatalogProduct] = []
    uuids: set[UUID] = set()
    slugs: set[str] = set()
    natural_key_members: dict[str, list[CatalogProduct]] = {}
    release_keys: dict[str, str] = {}
    identifier_keys: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(payload["products"]):
        if not isinstance(raw, dict):
            raise ValueError(  # noqa: TRY004
                f"invalid catalog product at index {index}: expected object"
            )
        try:
            canonical_uuid = UUID(str(raw["canonical_uuid"]))
            canonical_id = str(raw["canonical_id"])
            release_key = _release_key(raw, index=index)
            product_view = ProductView.model_validate(
                {field: raw.get(field) for field in ProductView.model_fields}
            )
        except Exception as error:
            raise ValueError(f"invalid catalog product at index {index}: {error}") from error
        if canonical_uuid in uuids or canonical_id in slugs:
            raise ValueError(f"duplicate catalog identity at index {index}")
        key = fingerprint(raw)
        raw_aliases = raw.get("aliases", [])
        raw_identifiers = raw.get("identifiers", [])
        if not isinstance(raw_aliases, list) or not isinstance(raw_identifiers, list):
            raise ValueError(f"invalid catalog collections at index {index}")  # noqa: TRY004
        typed_identifier_keys = [
            _typed_identifier_key(item, index=index) for item in raw_identifiers
        ]
        if len(typed_identifier_keys) != len(set(typed_identifier_keys)):
            raise ValueError(f"duplicate normalized identifier within product at index {index}")
        for identifier_key in typed_identifier_keys:
            owner = identifier_keys.get(identifier_key)
            if owner is not None:
                raise ValueError(f"normalized identifier collision: {canonical_id} and {owner}")
            identifier_keys[identifier_key] = canonical_id
        if release_key is not None:
            normalized_release_key = normalize_text(release_key)
            owner = release_keys.get(normalized_release_key)
            if owner is not None:
                raise ValueError(f"release_key collision: {canonical_id} and {owner}")
            release_keys[normalized_release_key] = canonical_id
        aliases = tuple(value for item in raw_aliases if (value := _alias_text(item)))
        identifiers = tuple(value for item in raw_identifiers if (value := _identifier_text(item)))
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
        catalog_product = CatalogProduct(
            canonical_uuid=canonical_uuid,
            canonical_id=canonical_id,
            product=product_view,
            aliases=aliases,
            identifiers=identifiers,
            provenance=provenance,
            alias_records=alias_records,
            identifier_records=identifier_records,
            release_key=release_key,
        )
        natural_key_members.setdefault(key, []).append(catalog_product)
        products.append(catalog_product)
    for colliding in natural_key_members.values():
        if len(colliding) < 2:
            continue
        if any(product.release_key is None for product in colliding):
            ids = ", ".join(product.canonical_id for product in colliding)
            raise ValueError(f"natural-key collision without release_key: {ids}")
        for catalog_product in colliding:
            if not any(
                normalize_text(record["identifier_type"]) == "toy_number"
                for record in catalog_product.identifier_records
            ):
                raise ValueError(
                    "natural-key collision requires a typed toy_number identifier: "
                    f"{catalog_product.canonical_id}"
                )
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

    rows: list[dict[str, Any]] = []
    for item in catalog.products:
        row = {
            "canonical_uuid": str(item.canonical_uuid),
            "canonical_id": item.canonical_id,
            "product": item.product.model_dump(mode="json"),
            "aliases": stable(item.alias_records or list(item.aliases)),
            "identifiers": stable(item.identifier_records or list(item.identifiers)),
            "provenance": stable(item.provenance),
        }
        if item.release_key is not None:
            row["release_key"] = item.release_key
        rows.append(row)
    rows.sort(key=lambda row: row["canonical_uuid"])
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_tokens(product: CatalogProduct) -> set[str]:
    return set(normalize_text(product.searchable_text).split())
