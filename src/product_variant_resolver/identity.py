from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from collections.abc import Mapping
from typing import Any

IDENTITY_FIELDS = (
    "brand", "casting", "release_year", "series", "color", "collector_number", "edition"
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w]+", value, flags=re.UNICODE))


def natural_key(product: Mapping[str, Any]) -> str:
    values = [normalize_text(str(product.get(field) or "")) for field in IDENTITY_FIELDS]
    return "\x1f".join(values)


def fingerprint(product: Mapping[str, Any]) -> str:
    return hashlib.sha256(natural_key(product).encode("utf-8")).hexdigest()


def mint_uuid(product: Mapping[str, Any], namespace: uuid.UUID = uuid.NAMESPACE_URL) -> uuid.UUID:
    return uuid.uuid5(namespace, "pvr:" + natural_key(product))


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "variant"


def mint_slug(product: Mapping[str, Any], existing: Mapping[str, str] | None = None) -> str:
    pieces = [str(product.get(field)) for field in IDENTITY_FIELDS if product.get(field) not in (None, "")]
    base = slugify("-".join(pieces))
    if not existing or base not in existing:
        return base
    key = fingerprint(product)
    if existing[base] == key:
        return base
    return f"{base}-{key[:8]}"


def assert_identity_immutable(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    for field in ("canonical_uuid", "canonical_id"):
        if str(before.get(field)) != str(after.get(field)):
            raise ValueError(f"immutable identity field changed: {field}")

