"""Build the private query-only source used by a future output-blind RHB-T5 session."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    SourceDecisionScope,
    SourceDecisionStatus,
    SourceDecisionUse,
    SourceDownstreamPermission,
    stable_json_bytes,
    validate_source_decisions,
    validate_t1_inventory_files,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
PRIVATE_AUTHORING_DIRECTORY = RHB_DIRECTORY / "local-query-authoring-v1"
PROJECTION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "output-blind-source.json"
MANIFEST_REFERENCE = RHB_DIRECTORY / "query-authoring-source-manifest.json"
HUMAN_SOURCE_REFERENCE = Path("data/human_labeled_names.json")
INVENTORY_REFERENCE = RHB_DIRECTORY / "source-inventory.json"
INVENTORY_MANIFEST_REFERENCE = RHB_DIRECTORY / "source-inventory-manifest.json"
SOURCE_DECISIONS_REFERENCE = RHB_DIRECTORY / "source-decisions.json"
WIKI_SOURCE_REFERENCE = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")

HUMAN_SOURCE_ID = "human-labeled-real-noisy-v1"
IGNORE_RULE = "/data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/"
NonBlank = Annotated[str, Field(min_length=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ProjectionError(ValueError):
    """Raised when the private projection cannot be reproduced safely."""


class ProjectionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)


class OutputBlindSourceRecord(ProjectionContract):
    source_record_ref: NonBlank
    query: NonBlank


class OutputBlindSourceProjection(ProjectionContract):
    schema_version: Literal["pvr-rhb-t5-output-blind-source-v1"]
    dataset_version: Literal["rhb-t5-output-blind-source-v1"]
    source_id: Literal["human-labeled-real-noisy-v1"]
    publication_scope: Literal["local_only"]
    source_file_sha256: Sha256
    source_record_count: Literal[101]
    projected_record_count: Literal[91]
    excluded_blank_query_count: Literal[10]
    field_allowlist: list[Literal["source_record_ref", "query"]]
    resolver_output_viewed: Literal[False]
    benchmark_labels_loaded: Literal[False]
    network_requests: Literal[0]
    records: list[OutputBlindSourceRecord] = Field(min_length=91, max_length=91)

    @model_validator(mode="after")
    def rows_are_complete_unique_and_ordered(self) -> OutputBlindSourceProjection:
        if self.field_allowlist != ["source_record_ref", "query"]:
            raise ValueError("output-blind projection field allowlist changed")
        if self.projected_record_count != len(self.records):
            raise ValueError("projection record count is inconsistent")
        if self.excluded_blank_query_count != self.source_record_count - len(self.records):
            raise ValueError("projection excluded count is inconsistent")
        refs = [record.source_record_ref for record in self.records]
        if refs != sorted(set(refs)):
            raise ValueError("projection source references must be unique and sorted")
        queries = [record.query.casefold() for record in self.records]
        if len(queries) != len(set(queries)):
            raise ValueError("projection query text must be unique")
        return self


class ProjectionPublicAggregate(ProjectionContract):
    source_record_count: Literal[101]
    projected_record_count: Literal[91]
    excluded_blank_query_count: Literal[10]
    duplicate_query_count: Literal[0]
    publication_scope: Literal["local_only"]
    contains_pipeline_outputs: Literal[False]
    contains_human_labels: Literal[False]
    contains_failure_categories: Literal[False]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]


class OutputBlindSourceManifest(ProjectionContract):
    schema_name: Literal["pvr-rhb-t5-output-blind-source-manifest-v1"] = Field(alias="schema")
    sha256: Sha256
    record_count: Literal[91]
    non_sensitive_aggregate: ProjectionPublicAggregate
    non_sensitive_summary: Literal[
        "Private query-only projection created; public Git contains no row-level query text."
    ]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProjectionError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise ProjectionError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ProjectionError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionError(message)


def _decision_for_use(source: Any, use: SourceDecisionUse) -> Any:
    return next(decision for decision in source.decisions if decision.use == use)


def _validated_human_source(root: Path) -> tuple[dict[str, Any], str]:
    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_payload = _load_object(root / SOURCE_DECISIONS_REFERENCE)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    human_payload = _load_object(root / HUMAN_SOURCE_REFERENCE)
    inventory, _manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    inventory_source = next(
        (entry for entry in inventory.entries if entry.source_id == HUMAN_SOURCE_ID), None
    )
    decision_source = next(
        (entry for entry in decisions.sources if entry.source_id == HUMAN_SOURCE_ID), None
    )
    _expect(inventory_source is not None, "human source is missing from inventory")
    _expect(decision_source is not None, "human source is missing from source decisions")
    assert inventory_source is not None
    assert decision_source is not None
    source_sha256 = _raw_sha256(root / HUMAN_SOURCE_REFERENCE)
    _expect(inventory_source.local_sha256 == source_sha256, "human source checksum drift")
    _expect(inventory_source.record_count == 101, "human source inventory count drift")
    _expect(
        SourceDownstreamPermission.query_pack in decision_source.downstream_permissions,
        "human source no longer grants query-pack use",
    )
    query_decision = _decision_for_use(decision_source, SourceDecisionUse.query_text)
    local_decision = _decision_for_use(decision_source, SourceDecisionUse.local_only_benchmark_use)
    public_decision = _decision_for_use(decision_source, SourceDecisionUse.public_git_artifacts)
    _expect(
        query_decision.status == SourceDecisionStatus.approved
        and query_decision.effective_publication_scope == SourceDecisionScope.local_only
        and query_decision.allowed_fields == ["query_text"],
        "human query permission must remain query-text-only and local-only",
    )
    _expect(
        local_decision.status == SourceDecisionStatus.approved
        and local_decision.effective_publication_scope == SourceDecisionScope.local_only,
        "human benchmark permission must remain local-only",
    )
    _expect(
        public_decision.status == SourceDecisionStatus.approved
        and public_decision.effective_publication_scope == SourceDecisionScope.aggregate_only,
        "human public Git permission must remain aggregate-only",
    )
    return human_payload, source_sha256


def build_output_blind_projection(
    root: Path,
) -> tuple[OutputBlindSourceProjection, OutputBlindSourceManifest]:
    """Build the expected private projection and safe public manifest in memory."""

    root = root.absolute()
    human_payload, source_sha256 = _validated_human_source(root)
    _expect(human_payload.get("dataset_version") == HUMAN_SOURCE_ID, "dataset version drift")
    source_records = human_payload.get("records")
    _expect(isinstance(source_records, list), "human source must contain records[]")
    assert isinstance(source_records, list)
    _expect(len(source_records) == 101, "human source must retain 101 records")

    records: list[dict[str, str]] = []
    source_refs: set[str] = set()
    normalized_queries: set[str] = set()
    blank_count = 0
    for index, source_record in enumerate(source_records):
        _expect(isinstance(source_record, Mapping), f"human source row {index} must be an object")
        assert isinstance(source_record, Mapping)
        source_ref = source_record.get("case_id")
        _expect(
            isinstance(source_ref, str) and bool(source_ref.strip()),
            f"human source row {index} lacks case_id",
        )
        assert isinstance(source_ref, str)
        _expect(source_ref not in source_refs, "human source contains duplicate case IDs")
        source_refs.add(source_ref)
        query = source_record.get("initial_name")
        if not isinstance(query, str) or not query.strip():
            blank_count += 1
            continue
        normalized = query.strip().casefold()
        _expect(normalized not in normalized_queries, "human source contains duplicate query text")
        normalized_queries.add(normalized)
        records.append({"query": query.strip(), "source_record_ref": source_ref})
    records.sort(key=lambda record: record["source_record_ref"])
    _expect(len(records) == 91 and blank_count == 10, "projection capacity changed from 91/10")

    projection = OutputBlindSourceProjection.model_validate(
        {
            "schema_version": "pvr-rhb-t5-output-blind-source-v1",
            "dataset_version": "rhb-t5-output-blind-source-v1",
            "source_id": HUMAN_SOURCE_ID,
            "publication_scope": "local_only",
            "source_file_sha256": source_sha256,
            "source_record_count": len(source_records),
            "projected_record_count": len(records),
            "excluded_blank_query_count": blank_count,
            "field_allowlist": ["source_record_ref", "query"],
            "resolver_output_viewed": False,
            "benchmark_labels_loaded": False,
            "network_requests": 0,
            "records": records,
        }
    )
    projection_raw = stable_json_bytes(projection.model_dump(mode="json"))
    manifest = OutputBlindSourceManifest.model_validate(
        {
            "schema": "pvr-rhb-t5-output-blind-source-manifest-v1",
            "sha256": hashlib.sha256(projection_raw).hexdigest(),
            "record_count": len(records),
            "non_sensitive_aggregate": {
                "source_record_count": len(source_records),
                "projected_record_count": len(records),
                "excluded_blank_query_count": blank_count,
                "duplicate_query_count": 0,
                "publication_scope": "local_only",
                "contains_pipeline_outputs": False,
                "contains_human_labels": False,
                "contains_failure_categories": False,
                "resolver_output_consulted": False,
                "benchmark_labels_consulted": False,
                "network_requests": 0,
            },
            "non_sensitive_summary": (
                "Private query-only projection created; public Git contains no row-level query text."
            ),
        }
    )
    return projection, manifest


def validate_materialized_projection(
    root: Path,
) -> tuple[OutputBlindSourceProjection, OutputBlindSourceManifest]:
    """Reproduce and validate both local/private and public halves of the projection."""

    root = root.absolute()
    expected_projection, expected_manifest = build_output_blind_projection(root)
    projection_path = root / PROJECTION_REFERENCE
    manifest_path = root / MANIFEST_REFERENCE
    _expect(projection_path.is_file() and not projection_path.is_symlink(), "projection is absent")
    _expect(manifest_path.is_file() and not manifest_path.is_symlink(), "manifest is absent")
    _expect(
        stat.S_IMODE(projection_path.stat().st_mode) == 0o600,
        "private projection must use mode 0600",
    )
    _expect(
        stat.S_IMODE(manifest_path.stat().st_mode) == 0o644,
        "public projection manifest must use mode 0644",
    )
    actual_projection = OutputBlindSourceProjection.model_validate(_load_object(projection_path))
    actual_manifest = OutputBlindSourceManifest.model_validate(_load_object(manifest_path))
    _expect(actual_projection == expected_projection, "materialized projection is stale")
    _expect(actual_manifest == expected_manifest, "materialized projection manifest is stale")
    _expect(
        actual_manifest.sha256 == hashlib.sha256(projection_path.read_bytes()).hexdigest(),
        "projection manifest checksum differs from private bytes",
    )
    return actual_projection, actual_manifest


def _require_ignore_rule(root: Path) -> None:
    try:
        rules = root.joinpath(".gitignore").read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ProjectionError("could not read .gitignore") from error
    _expect(IGNORE_RULE in rules, "private authoring directory lacks an exact .gitignore rule")


def _write_temp(target: Path, raw: bytes, mode: int) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def materialize_output_blind_projection(
    root: Path, *, check: bool = False
) -> Literal["created", "unchanged"]:
    """Atomically install the private projection and its aggregate-only public manifest."""

    root = root.absolute()
    _require_ignore_rule(root)
    projection, manifest = build_output_blind_projection(root)
    targets = {
        PROJECTION_REFERENCE: root / PROJECTION_REFERENCE,
        MANIFEST_REFERENCE: root / MANIFEST_REFERENCE,
    }
    states = {reference: path.exists() for reference, path in targets.items()}
    expected = {
        PROJECTION_REFERENCE: stable_json_bytes(projection.model_dump(mode="json")),
        MANIFEST_REFERENCE: stable_json_bytes(manifest.model_dump(mode="json", by_alias=True)),
    }
    if states[PROJECTION_REFERENCE] and not states[MANIFEST_REFERENCE]:
        raise ProjectionError("private projection exists without its public manifest")
    if states[MANIFEST_REFERENCE] and not states[PROJECTION_REFERENCE]:
        manifest_path = targets[MANIFEST_REFERENCE]
        _expect(
            manifest_path.is_file() and not manifest_path.is_symlink(),
            "public projection manifest is unsafe",
        )
        _expect(
            stat.S_IMODE(manifest_path.stat().st_mode) == 0o644,
            "public projection manifest must use mode 0644",
        )
        actual_manifest = OutputBlindSourceManifest.model_validate(_load_object(manifest_path))
        _expect(actual_manifest == manifest, "public projection manifest is stale")
        _expect(
            manifest_path.read_bytes() == expected[MANIFEST_REFERENCE],
            "public projection manifest bytes are stale",
        )
    if all(states.values()):
        validate_materialized_projection(root)
        if all(targets[reference].read_bytes() == raw for reference, raw in expected.items()):
            return "unchanged"
        raise ProjectionError("materialized projection differs from expected bytes")
    if check:
        raise ProjectionError("output-blind projection is not materialized")

    private_directory = root / PRIVATE_AUTHORING_DIRECTORY
    private_directory.mkdir(parents=True, exist_ok=True)
    os.chmod(private_directory, 0o700)
    temps: list[Path] = []
    installed: list[Path] = []
    references_to_write = [reference for reference in targets if not states[reference]]
    try:
        for reference in references_to_write:
            target = targets[reference]
            mode = 0o600 if reference == PROJECTION_REFERENCE else 0o644
            temps.append(_write_temp(target, expected[reference], mode))
        for reference, temp in zip(references_to_write, temps, strict=True):
            target = targets[reference]
            os.replace(temp, target)
            os.chmod(target, 0o600 if reference == PROJECTION_REFERENCE else 0o644)
            installed.append(target)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        for target in reversed(installed):
            if target.exists() and not target.is_symlink():
                target.unlink()
        raise
    validate_materialized_projection(root)
    return "created"


__all__ = [
    "IGNORE_RULE",
    "MANIFEST_REFERENCE",
    "PRIVATE_AUTHORING_DIRECTORY",
    "PROJECTION_REFERENCE",
    "OutputBlindSourceManifest",
    "OutputBlindSourceProjection",
    "ProjectionError",
    "build_output_blind_projection",
    "materialize_output_blind_projection",
    "validate_materialized_projection",
]
