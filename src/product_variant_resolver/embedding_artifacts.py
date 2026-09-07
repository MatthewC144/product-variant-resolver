from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .catalog import Catalog


DENSE_TEXT_VERSION = "catalog-searchable-text-v1"


class VersionedEmbedding(Protocol):
    version: str
    dimensions: int

    def encode(self, text: str) -> tuple[float, ...]: ...


@dataclass(frozen=True, slots=True)
class EmbeddingRow:
    canonical_uuid: UUID
    embedding_version: str
    vector_literal: str
    checksum: str


def embedding_artifact_version(model: VersionedEmbedding) -> str:
    return f"{model.version}-d{model.dimensions}-{DENSE_TEXT_VERSION}"


def vector_literal(vector: tuple[float, ...]) -> str:
    return "[" + ",".join(format(value, ".9g") for value in vector) + "]"


def build_embedding_rows(
    catalog: Catalog, model: VersionedEmbedding
) -> tuple[EmbeddingRow, ...]:
    version = embedding_artifact_version(model)
    rows: list[EmbeddingRow] = []
    for product in sorted(catalog.products, key=lambda item: str(item.canonical_uuid)):
        literal = vector_literal(model.encode(product.searchable_text))
        checksum_payload = json.dumps(
            {
                "canonical_uuid": str(product.canonical_uuid),
                "embedding_version": version,
                "searchable_text": product.searchable_text,
                "vector": literal,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        rows.append(
            EmbeddingRow(
                canonical_uuid=product.canonical_uuid,
                embedding_version=version,
                vector_literal=literal,
                checksum=hashlib.sha256(checksum_payload.encode("utf-8")).hexdigest(),
            )
        )
    return tuple(rows)


def embedding_index_checksum(rows: tuple[EmbeddingRow, ...]) -> str:
    payload = "\n".join(f"{row.canonical_uuid}:{row.checksum}" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
