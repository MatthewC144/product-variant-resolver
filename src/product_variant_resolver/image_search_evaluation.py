"""Source-relative evaluation for the frozen image-search resolver dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ConfigDict, Field, field_validator, model_validator

from .catalog import Catalog, CatalogProduct
from .config import Settings
from .evaluation import percentile, safe_divide
from .human_knowledge import load_human_knowledge_catalog
from .identity import normalize_text
from .schemas import ProductView, ResolutionStatus, ResolveRequest, StrictModel
from .service import ResolverService
from .signals import extract_signals

DATASET = Path("data/evaluation/image-search-resolver-v1/dataset.json")
SOURCE = Path("data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json")
SOURCE_COUNT = 1_763
SOURCE_USAGE = "staging_only_not_evaluation_or_canonical"
SOURCE_STATUS = "review_only_local_staging_snapshot"
FROZEN_DATASET_SHA256 = "b0feeff8f1158ab67cfac2ae493eefc04a6aba1b90d4fce448724341315e095c"
FROZEN_DATASET_COUNT = 153
FROZEN_DEVELOPMENT_COUNT = 100
FROZEN_SPLIT_VERSION = "image-search-release-ranking-split-v1"
FROZEN_SPLIT_SALT = "pvr:image-search-release-ranking:development-test:v1"
FROZEN_SPLIT_SHA256 = "10ed70cc347f1b548c156e033645d6b0e90f48ee66c95af631832e8d55aebdac"
AUTHORITY_NOTE = (
    "Expected identities are relative to the frozen third-party release source; they are not "
    "Mattel/manufacturer-certified or global canonical truth."
)

SplitName = Literal["development", "test", "all"]


class ExpectedFullIdentity(StrictModel):
    brand: str = Field(min_length=1)
    casting: str = Field(min_length=1)
    release_year: int = Field(ge=1968, le=2100)
    series: str = Field(min_length=1)
    collector_number: str = Field(min_length=1)
    series_position: str = Field(min_length=1)
    toy_number: str = Field(min_length=1)
    color: str | None = None
    variant_note: str | None = None

    @field_validator(
        "brand",
        "casting",
        "series",
        "collector_number",
        "series_position",
        "toy_number",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required identity text must not be blank")
        return stripped


class ImageSearchCase(StrictModel):
    id: str = Field(pattern=r"^isr-[0-9]{4}$")
    query: str = Field(min_length=1, max_length=500)
    expected_casting: str = Field(min_length=1)
    expected_full_identity: ExpectedFullIdentity

    @field_validator("query", "expected_casting")
    @classmethod
    def strip_case_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("case text must not be blank")
        return stripped

    @model_validator(mode="after")
    def casting_agrees(self) -> ImageSearchCase:
        if normalize_text(self.expected_casting) != normalize_text(
            self.expected_full_identity.casting
        ):
            raise ValueError("expected_casting differs from expected_full_identity.casting")
        return self


class ImageSearchDataset(StrictModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(pattern=r"^image-search-resolver-v[0-9]+$")
    records: list[ImageSearchCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset_members(self) -> ImageSearchDataset:
        expected_ids = [f"isr-{index:04d}" for index in range(1, len(self.records) + 1)]
        if [case.id for case in self.records] != expected_ids:
            raise ValueError("case IDs must be contiguous and ordered")
        queries = [normalize_text(case.query) for case in self.records]
        if len(queries) != len(set(queries)):
            raise ValueError("normalized queries must be unique")
        castings = [normalize_text(case.expected_casting) for case in self.records]
        if len(castings) != len(set(castings)):
            raise ValueError("normalized expected castings must be unique")
        return self


@dataclass(frozen=True, slots=True)
class SourceBinding:
    case_id: str
    source_record_id: str
    toy_number: str
    evaluation_uuid: UUID


@dataclass(frozen=True, slots=True)
class FrozenSplit:
    version: str
    development_case_ids: tuple[str, ...]
    test_case_ids: tuple[str, ...]
    assignment_sha256: str


@dataclass(frozen=True, slots=True)
class ImageSearchEvaluationReport:
    schema_version: str
    dataset_version: str
    catalog_version: str
    split: str
    split_version: str
    split_assignment_sha256: str
    full_dataset_count: int
    sample_count: int
    candidate_count: int
    source_binding_count: int
    casting_top1_accuracy: float
    exact_release_top1_accuracy: float
    exact_release_recall_at_10: float
    exact_release_recall_at_25: float
    policy_exact_accuracy: float
    policy_precision: float
    policy_coverage: float
    policy_abstention_rate: float
    policy_status_counts: dict[str, int]
    pipeline_p50_latency_ms: float
    pipeline_p95_latency_ms: float
    raw_counts: dict[str, int]
    metadata: dict[str, Any]


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def load_image_search_dataset(path: Path = DATASET) -> ImageSearchDataset:
    return ImageSearchDataset.model_validate(_read_object(path))


def build_deterministic_split(
    dataset: ImageSearchDataset,
    *,
    development_count: int,
    salt: str,
    version: str,
) -> FrozenSplit:
    if not 1 <= development_count < len(dataset.records):
        raise ValueError("development_count must leave at least one test case")
    if not salt.strip() or not version.strip():
        raise ValueError("split salt and version must not be blank")
    keyed = sorted(
        dataset.records,
        key=lambda case: hashlib.sha256(
            f"{salt}\0{case.id}\0{normalize_text(case.expected_casting)}".encode()
        ).hexdigest(),
    )
    development_ids = frozenset(case.id for case in keyed[:development_count])
    test_ids = frozenset(case.id for case in keyed[development_count:])
    if development_ids & test_ids or len(development_ids | test_ids) != len(dataset.records):
        raise ValueError("split must be disjoint and exhaustive")
    assignments = [
        {
            "case_id": case.id,
            "split": "development" if case.id in development_ids else "test",
        }
        for case in dataset.records
    ]
    assignment_bytes = json.dumps(
        assignments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return FrozenSplit(
        version=version,
        development_case_ids=tuple(
            case.id for case in dataset.records if case.id in development_ids
        ),
        test_case_ids=tuple(case.id for case in dataset.records if case.id in test_ids),
        assignment_sha256=hashlib.sha256(assignment_bytes).hexdigest(),
    )


def load_frozen_split(dataset: ImageSearchDataset, dataset_path: Path = DATASET) -> FrozenSplit:
    dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    if dataset_sha256 != FROZEN_DATASET_SHA256 or len(dataset.records) != FROZEN_DATASET_COUNT:
        raise ValueError("dataset bytes or row count differ from the frozen split contract")
    split = build_deterministic_split(
        dataset,
        development_count=FROZEN_DEVELOPMENT_COUNT,
        salt=FROZEN_SPLIT_SALT,
        version=FROZEN_SPLIT_VERSION,
    )
    if FROZEN_SPLIT_SHA256 and split.assignment_sha256 != FROZEN_SPLIT_SHA256:
        raise ValueError("split assignment differs from the frozen checksum")
    return split


def load_source_records(
    path: Path = SOURCE, *, expected_count: int = SOURCE_COUNT
) -> list[dict[str, Any]]:
    payload = _read_object(path)
    if payload.get("schema_version") != "pvr-local-release-staging-v1":
        raise ValueError("unexpected source schema")
    if payload.get("status") != SOURCE_STATUS:
        raise ValueError("source is not the frozen review-only snapshot")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != expected_count:
        raise ValueError(f"source must contain exactly {expected_count} records")
    source_ids: set[str] = set()
    toy_numbers: set[str] = set()
    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            raise TypeError(f"source record {index} must be an object")
        source_id = _source_text(raw, "source_record_id", index)
        toy_number = _source_text(raw, "toy_number", index)
        if raw.get("usage") != SOURCE_USAGE or raw.get("canonical_uuid") is not None:
            raise ValueError(f"source record {index} crosses the staging authority boundary")
        if source_id in source_ids or toy_number in toy_numbers:
            raise ValueError("source IDs and toy numbers must be unique")
        source_ids.add(source_id)
        toy_numbers.add(toy_number)
    return records


def _source_text(raw: dict[str, Any], field: str, index: int) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"source record {index} has invalid {field}")
    return value.strip()


def _evaluation_uuid(source_record_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"pvr:image-search-evaluation:{source_record_id}")


def _identity_values(case: ImageSearchCase) -> dict[str, Any]:
    return case.expected_full_identity.model_dump(mode="python")


def bind_dataset_to_source(
    dataset: ImageSearchDataset, records: list[dict[str, Any]]
) -> list[SourceBinding]:
    by_toy = {_source_text(raw, "toy_number", index): raw for index, raw in enumerate(records)}
    bindings: list[SourceBinding] = []
    field_map = {
        "brand": "brand",
        "casting": "casting_name",
        "release_year": "release_year",
        "series": "series",
        "collector_number": "collector_number",
        "series_position": "series_position",
        "toy_number": "toy_number",
        "color": "color",
        "variant_note": "variant_note",
    }
    for case in dataset.records:
        identity = _identity_values(case)
        raw = by_toy.get(case.expected_full_identity.toy_number)
        if raw is None:
            raise ValueError(f"{case.id}: toy number is absent from the source snapshot")
        for expected_field, source_field in field_map.items():
            expected = identity[expected_field]
            actual = raw.get(source_field)
            if isinstance(expected, str) and isinstance(actual, str):
                agrees = normalize_text(expected) == normalize_text(actual)
            else:
                agrees = expected == actual
            if not agrees:
                raise ValueError(f"{case.id}: source mismatch for {expected_field}")
        source_id = _source_text(raw, "source_record_id", 0)
        bindings.append(
            SourceBinding(
                case_id=case.id,
                source_record_id=source_id,
                toy_number=case.expected_full_identity.toy_number,
                evaluation_uuid=_evaluation_uuid(source_id),
            )
        )
    return bindings


def build_evaluation_catalog(records: list[dict[str, Any]]) -> Catalog:
    products: list[CatalogProduct] = []
    for index, raw in enumerate(records):
        source_id = _source_text(raw, "source_record_id", index)
        toy_number = _source_text(raw, "toy_number", index)
        casting = _source_text(raw, "casting_name", index)
        model_label = _source_text(raw, "source_model_label", index)
        aliases = tuple(dict.fromkeys((casting, model_label)))
        products.append(
            CatalogProduct(
                canonical_uuid=_evaluation_uuid(source_id),
                canonical_id=f"evaluation-release-{source_id}",
                product=ProductView(
                    brand=_source_text(raw, "brand", index),
                    casting=casting,
                    release_year=int(raw["release_year"]),
                    series=_source_text(raw, "series", index),
                    color=raw.get("color"),
                    collector_number=_source_text(raw, "collector_number", index),
                    series_position=_source_text(raw, "series_position", index),
                    rarity_tier=None,
                    edition=None,
                ),
                aliases=aliases,
                identifiers=(toy_number, _source_text(raw, "collector_number", index)),
                provenance=(
                    {
                        "source_name": "owner_local_third_party_release_snapshot",
                        "source_record_id": source_id,
                        "authority": "evaluation_only_not_canonical",
                    },
                ),
                alias_records=tuple(
                    {
                        "alias_text": alias,
                        "alias_type": "source_label",
                        "source_id": source_id,
                    }
                    for alias in aliases
                ),
                identifier_records=(
                    {
                        "identifier_type": "toy_number",
                        "identifier_value": toy_number,
                        "source_id": source_id,
                    },
                    {
                        "identifier_type": "collector_number",
                        "identifier_value": _source_text(raw, "collector_number", index),
                        "source_id": source_id,
                    },
                ),
                release_key=f"{raw['release_year']}:{toy_number}",
            )
        )
    return Catalog("image-search-evaluation-source-1763-v1", products)


def evaluate_image_search_dataset(
    settings: Settings,
    *,
    dataset_path: Path = DATASET,
    source_path: Path = SOURCE,
    source_expected_count: int = SOURCE_COUNT,
    split: SplitName = "development",
) -> ImageSearchEvaluationReport:
    dataset = load_image_search_dataset(dataset_path)
    records = load_source_records(source_path, expected_count=source_expected_count)
    bindings = bind_dataset_to_source(dataset, records)
    target_by_case = {binding.case_id: binding.evaluation_uuid for binding in bindings}
    frozen_split: FrozenSplit | None = None
    if split == "all":
        cases = dataset.records
    else:
        frozen_split = load_frozen_split(dataset, dataset_path)
        selected_ids = set(
            frozen_split.development_case_ids
            if split == "development"
            else frozen_split.test_case_ids
        )
        cases = [case for case in dataset.records if case.id in selected_ids]
    catalog = build_evaluation_catalog(records)
    human_catalog = load_human_knowledge_catalog(
        settings.human_catalog_path,
        settings.review_family_knowledge_path,
        settings.review_family_knowledge_manifest_path,
    )
    service = ResolverService(settings, catalog, human_catalog)

    casting_top1 = exact_top1 = recall10 = recall25 = 0
    policy_exact = policy_matches = 0
    status_counts = {status.value: 0 for status in ResolutionStatus}
    latencies: list[float] = []
    for case in cases:
        signals = extract_signals(case.query, service.color_vocabulary, service.series_vocabulary)
        candidates = service.retrieval.retrieve(signals, settings.candidate_limit)
        if settings.reranker_enabled:
            candidates = service.reranker.rerank(signals, candidates)
        target = target_by_case[case.id]
        rank = next(
            (
                index
                for index, candidate in enumerate(candidates, start=1)
                if candidate.product.canonical_uuid == target
            ),
            None,
        )
        if candidates:
            casting_top1 += normalize_text(candidates[0].product.product.casting) == normalize_text(
                case.expected_casting
            )
            exact_top1 += candidates[0].product.canonical_uuid == target
        recall10 += rank is not None and rank <= 10
        recall25 += rank is not None and rank <= 25

        started = time.perf_counter()
        response = service.resolve(ResolveRequest(title=case.query))
        latencies.append((time.perf_counter() - started) * 1000)
        status_counts[response.status.value] += 1
        if response.status is ResolutionStatus.matched:
            policy_matches += 1
            policy_exact += response.canonical_uuid == target

    sample_count = len(cases)
    return ImageSearchEvaluationReport(
        schema_version="pvr-image-search-evaluation-report-v1",
        dataset_version=dataset.dataset_version,
        catalog_version=catalog.version,
        split=split,
        split_version=(frozen_split.version if frozen_split else "unfrozen-all-test-helper"),
        split_assignment_sha256=(
            frozen_split.assignment_sha256 if frozen_split else "not-applicable"
        ),
        full_dataset_count=len(dataset.records),
        sample_count=sample_count,
        candidate_count=len(catalog.products),
        source_binding_count=len(bindings),
        casting_top1_accuracy=safe_divide(casting_top1, sample_count),
        exact_release_top1_accuracy=safe_divide(exact_top1, sample_count),
        exact_release_recall_at_10=safe_divide(recall10, sample_count),
        exact_release_recall_at_25=safe_divide(recall25, sample_count),
        policy_exact_accuracy=safe_divide(policy_exact, sample_count),
        policy_precision=safe_divide(policy_exact, policy_matches),
        policy_coverage=safe_divide(policy_matches, sample_count),
        policy_abstention_rate=safe_divide(sample_count - policy_matches, sample_count),
        policy_status_counts=status_counts,
        pipeline_p50_latency_ms=statistics.median(latencies) if latencies else 0.0,
        pipeline_p95_latency_ms=percentile(latencies, 0.95),
        raw_counts={
            "casting_top1_correct": casting_top1,
            "exact_release_top1_correct": exact_top1,
            "exact_release_retrieved_at_10": recall10,
            "exact_release_retrieved_at_25": recall25,
            "policy_matches": policy_matches,
            "policy_exact_correct": policy_exact,
        },
        metadata={
            "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "source_snapshot_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "candidate_limit": settings.candidate_limit,
            "reranker_enabled": settings.reranker_enabled,
            "row_level_output_persisted": False,
            "canonical_catalog_modified": False,
            "evaluation_identity": "deterministic surrogate UUIDv5",
            "authority_note": AUTHORITY_NOTE,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the local image-search benchmark")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--split", choices=("development", "test"), default="development")
    parser.add_argument("--acknowledge-source-relative-evaluation", action="store_true")
    arguments = parser.parse_args()
    if not arguments.acknowledge_source_relative_evaluation:
        parser.error("--acknowledge-source-relative-evaluation is required")
    report = evaluate_image_search_dataset(
        Settings.from_env(),
        dataset_path=arguments.dataset,
        source_path=arguments.source,
        split=cast(SplitName, arguments.split),
    )
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
