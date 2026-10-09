"""DRSP-T2 family-safe partitions and frozen candidate pools.

The public artifacts produced here contain only aggregate counts and irreversible
digests.  Case membership, queries, labels, candidate identities/text, and generic
scores stay in the default-deny ``local-t2`` directory.

This module deliberately does not mine negatives, train/select a model, fit a
calibrator, evaluate a final set, or change runtime behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import stat
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from .domain_ranker_governance import (
    CATALOG_PATH,
    CATALOG_SHA256,
    GOVERNANCE_V2_PATH,
    NEGATIVE_HOLDOUT_COUNT,
    POSITIVE_DATASET_PATH,
    POSITIVE_DATASET_SHA256,
    POSITIVE_DEVELOPMENT_COUNT,
    POSITIVE_SPLIT_SHA256,
    POSITIVE_TEST_COUNT,
    check_publication_amendment,
)
from .identity import normalize_text
from .image_search_evaluation import (
    ImageSearchCase,
    build_evaluation_catalog,
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)
from .neural_reranker_comparison import freeze_candidate
from .neural_reranking import (
    POINTWISE_MODEL_ID,
    POINTWISE_REVISION,
    LocalPointwiseScorer,
    load_pointwise_model_config,
    rank_scores,
    render_candidate_text,
    validate_local_pointwise_model,
)
from .pointwise_no_match_governance import (
    CANDIDATE_SET_SHA256 as NO_MATCH_CANDIDATE_SET_SHA256,
)
from .pointwise_no_match_governance import (
    SPLIT_ASSIGNMENT_SHA256 as NO_MATCH_SPLIT_SHA256,
)
from .pointwise_no_match_readiness import FIT_COUNT, SELECTION_COUNT
from .retrieval import (
    CandidateRetrievalService,
    DenseRetriever,
    HashingEmbedding,
    SparseRetriever,
    StructuredRetriever,
)
from .signals import extract_signals

VERSION = "domain-ranker-selective-prediction-development-v1"
SCHEMA_AUTHORIZATION = "pvr-drsp-t2-owner-authorization-v1"
SCHEMA_LOCAL_PARTITIONS = "pvr-drsp-t2-local-partitions-v1"
SCHEMA_SPLIT_MANIFEST = "pvr-drsp-t2-split-manifest-v1"
SCHEMA_LOCAL_POOLS = "pvr-drsp-t2-local-candidate-pools-v1"
SCHEMA_POOL_MANIFEST = "pvr-drsp-t2-candidate-pool-manifest-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-selective-prediction-development-v1")
AUTHORIZATION_PATH = DIRECTORY / "t2-owner-authorization.json"
SPLIT_MANIFEST_PATH = DIRECTORY / "split-manifest.json"
POOL_MANIFEST_PATH = DIRECTORY / "candidate-pool-manifest.json"
LOCAL_DIRECTORY = DIRECTORY / "local-t2"
LOCAL_PARTITIONS_PATH = LOCAL_DIRECTORY / "partitions.json"
LOCAL_POOLS_PATH = LOCAL_DIRECTORY / "candidate-pools.json"

POINTWISE_CONFIG_PATH = Path("config/neural-reranker-comparison-v1.json")
POINTWISE_MODEL_PATH = Path("model-cache/neural-reranker-comparison-v1/pointwise")

FROZEN_EFFECTIVE_GOVERNANCE_FILE_SHA256 = (
    "2ce83d6790f05ad4c580f835b2b749809ce906860c37f4f385b8512a60937302"
)
FROZEN_POINTWISE_CONFIG_SHA256 = (
    "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6"
)
FROZEN_POINTWISE_MANIFEST_SHA256 = (
    "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
)
OWNER_STATEMENT_SHA256 = "bc5a1f005607f49fac6fc1f106e97e825e57c1c1ce9b9df607e638a804b0083e"

PARTITION_SALT = "pvr:drsp-t2:family-evidence-safe-ranker-partitions:v1"
PRIVATE_DIGEST_SALT = "pvr:drsp-t2:private-assignment-digest:v1"
RANKER_TRAIN_TARGET = 70
RANKER_TRAIN_MINIMUM = 50
RANKER_SELECTION_MINIMUM = 15
CANDIDATE_LIMIT = 25
DENSE_DIMENSIONS = 192
RRF_K = 60

CODE_PATHS = (
    Path("src/product_variant_resolver/domain_ranker_partitions.py"),
    Path("src/product_variant_resolver/domain_ranker_governance.py"),
    Path("src/product_variant_resolver/image_search_evaluation.py"),
    Path("src/product_variant_resolver/neural_reranker_comparison.py"),
    Path("src/product_variant_resolver/neural_reranking.py"),
    Path("src/product_variant_resolver/retrieval.py"),
    Path("src/product_variant_resolver/signals.py"),
)

_PUBLIC_FORBIDDEN_KEYS = frozenset(
    {
        "assignment",
        "assignments",
        "candidate",
        "candidates",
        "case",
        "case_id",
        "case_ids",
        "expected_casting",
        "expected_full_identity",
        "label",
        "labels",
        "prediction",
        "predictions",
        "query",
        "queries",
        "record",
        "records",
        "row",
        "rows",
    }
)


class PointwiseScorer(Protocol):
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]: ...


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{path}: required regular file is absent or unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, expected: str, name: str) -> None:
    if _file_sha256(path) != expected:
        raise ValueError(f"{name} differs from the frozen SHA-256 binding")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _contains_public_row_level_data(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and key in _PUBLIC_FORBIDDEN_KEYS)
            or _contains_public_row_level_data(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_public_row_level_data(child) for child in value)
    return False


def _validate_t1_chain(root: Path) -> dict[str, Any]:
    _require_file(
        root / GOVERNANCE_V2_PATH,
        FROZEN_EFFECTIVE_GOVERNANCE_FILE_SHA256,
        "effective DRSP-T1A governance",
    )
    effective = check_publication_amendment(root, require_local_catalog=True)
    if effective.get("next_allowed_action") != "separate_owner_authorization_for_drsp_t2":
        raise ValueError("effective governance does not permit the DRSP-T2 owner Gate")
    if effective.get("permissions", {}).get("runtime_activation") is not False:
        raise ValueError("runtime activation boundary differs from DRSP-T1A")
    return effective


def build_authorization(root: Path) -> dict[str, Any]:
    effective = _validate_t1_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRSP-T2",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "execute_only_family_safe_partitions_and_frozen_candidate_pools",
        "parent_effective_governance": {
            "file_sha256": FROZEN_EFFECTIVE_GOVERNANCE_FILE_SHA256,
            "content_sha256": effective["effective_governance_sha256"],
        },
        "authorized_actions": [
            "partition_frozen_positive_development_into_ranker_train_and_ranker_selection",
            "freeze_query_only_retrieval_top_25_candidate_pools",
            "score_frozen_pools_once_with_pinned_generic_cross_encoder",
            "publish_aggregate_manifests_and_irreversible_digests",
        ],
        "data_boundary": {
            "positive_development_count": POSITIVE_DEVELOPMENT_COUNT,
            "positive_test_permanently_excluded_count": POSITIVE_TEST_COUNT,
            "negative_holdout_permanently_excluded_count": NEGATIVE_HOLDOUT_COUNT,
            "no_match_calibration_fit_count": FIT_COUNT,
            "no_match_threshold_selection_count": SELECTION_COUNT,
            "no_match_ranker_use_allowed": False,
        },
        "publication_boundary": {
            "aggregate_manifests": True,
            "irreversible_digests": True,
            "partition_membership": False,
            "queries_or_labels": False,
            "candidate_identities_text_or_scores": False,
        },
        "prohibited_actions": [
            "hard_negative_mining",
            "model_training_or_fine_tuning",
            "model_selection",
            "calibration_fit_or_threshold_selection",
            "fresh_final_read_or_scoring",
            "runtime_change_or_activation",
            "target_injection_into_retrieval_pool",
        ],
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("DRSP-T2 authorization contains row-level output")
    return result


def _source_record_for_case(
    case: ImageSearchCase, source_by_toy: Mapping[str, Mapping[str, Any]]
) -> Mapping[str, Any]:
    raw = source_by_toy.get(case.expected_full_identity.toy_number)
    if raw is None:
        raise ValueError(f"{case.id}: target toy number is absent from frozen catalog")
    expected = case.expected_full_identity.model_dump(mode="python")
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
    for expected_name, source_name in field_map.items():
        expected_value = expected[expected_name]
        source_value = raw.get(source_name)
        if isinstance(expected_value, str) and isinstance(source_value, str):
            agrees = normalize_text(expected_value) == normalize_text(source_value)
        else:
            agrees = expected_value == source_value
        if not agrees:
            raise ValueError(f"{case.id}: target differs from source field {expected_name}")
    return raw


def _case_group_keys(case: ImageSearchCase, source: Mapping[str, Any]) -> tuple[str, ...]:
    identity = case.expected_full_identity
    family = f"{normalize_text(identity.brand)}\0{normalize_text(identity.casting)}"
    exact = _content_sha256(identity.model_dump(mode="json"))
    aliases = {
        normalize_text(value)
        for value in (source.get("casting_name"), source.get("source_model_label"))
        if isinstance(value, str) and normalize_text(value)
    }
    source_id = source.get("source_record_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError(f"{case.id}: source evidence event is missing")
    keys = {
        f"family:{family}",
        f"identity:{exact}",
        f"query:{normalize_text(case.query)}",
        f"evidence:{normalize_text(source_id)}",
    }
    keys.update(f"alias:{normalize_text(identity.brand)}\0{alias}" for alias in aliases)
    return tuple(sorted(keys))


def _connected_components(
    cases: Sequence[ImageSearchCase], source_by_toy: Mapping[str, Mapping[str, Any]]
) -> list[list[ImageSearchCase]]:
    parent = {case.id: case.id for case in cases}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    owner_by_key: dict[str, str] = {}
    for case in cases:
        source = _source_record_for_case(case, source_by_toy)
        for key in _case_group_keys(case, source):
            owner = owner_by_key.setdefault(key, case.id)
            union(owner, case.id)

    grouped: dict[str, list[ImageSearchCase]] = defaultdict(list)
    for case in cases:
        grouped[find(case.id)].append(case)
    return [sorted(component, key=lambda item: item.id) for component in grouped.values()]


def _partition_components(components: Sequence[Sequence[ImageSearchCase]]) -> dict[str, str]:
    ordered = sorted(
        components,
        key=lambda component: hashlib.sha256(
            f"{PARTITION_SALT}\0{_content_sha256(sorted(case.id for case in component))}".encode()
        ).hexdigest(),
    )
    prefix_sizes = [0]
    for component in ordered:
        prefix_sizes.append(prefix_sizes[-1] + len(component))
    feasible = [
        index
        for index, train_count in enumerate(prefix_sizes)
        if train_count >= RANKER_TRAIN_MINIMUM
        and POSITIVE_DEVELOPMENT_COUNT - train_count >= RANKER_SELECTION_MINIMUM
    ]
    if not feasible:
        raise ValueError("family-safe components cannot satisfy minimum ranker partition counts")
    boundary = min(
        feasible,
        key=lambda index: (abs(prefix_sizes[index] - RANKER_TRAIN_TARGET), index),
    )
    train_ids = {case.id for component in ordered[:boundary] for case in component}
    result = {
        case.id: "ranker_train" if case.id in train_ids else "ranker_selection"
        for component in ordered
        for case in component
    }
    if len(result) != POSITIVE_DEVELOPMENT_COUNT:
        raise ValueError("ranker partition assignment is not exhaustive")
    return result


def build_partitions(root: Path, authorization: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if dict(authorization) != build_authorization(root):
        raise ValueError("DRSP-T2 owner authorization is stale or out of scope")
    dataset_path = root / POSITIVE_DATASET_PATH
    _require_file(dataset_path, POSITIVE_DATASET_SHA256, "positive dataset")
    dataset = load_image_search_dataset(dataset_path)
    frozen = load_frozen_split(dataset, dataset_path)
    if frozen.assignment_sha256 != POSITIVE_SPLIT_SHA256:
        raise ValueError("positive development/test split binding changed")
    development_ids = set(frozen.development_case_ids)
    cases = [case for case in dataset.records if case.id in development_ids]
    if len(cases) != POSITIVE_DEVELOPMENT_COUNT:
        raise ValueError("positive development count changed")

    source_records = load_source_records(root / CATALOG_PATH)
    source_by_toy: dict[str, Mapping[str, Any]] = {}
    for raw in source_records:
        toy_number = raw.get("toy_number")
        if not isinstance(toy_number, str) or toy_number in source_by_toy:
            raise ValueError("catalog toy-number index is invalid")
        source_by_toy[toy_number] = raw

    components = _connected_components(cases, source_by_toy)
    assignment = _partition_components(components)
    component_by_case: dict[str, str] = {}
    component_sizes: Counter[int] = Counter()
    for component in components:
        component_digest = hashlib.sha256(
            f"{PRIVATE_DIGEST_SALT}\0component\0{_content_sha256(sorted(c.id for c in component))}".encode()
        ).hexdigest()
        component_sizes[len(component)] += 1
        for case in component:
            component_by_case[case.id] = component_digest

    members: list[dict[str, Any]] = []
    group_values: dict[str, dict[str, set[str]]] = {
        "ranker_train": defaultdict(set),
        "ranker_selection": defaultdict(set),
    }
    for case in sorted(cases, key=lambda item: item.id):
        source = _source_record_for_case(case, source_by_toy)
        partition = assignment[case.id]
        keys = _case_group_keys(case, source)
        for key in keys:
            namespace, value = key.split(":", 1)
            group_values[partition][namespace].add(value)
        source_id = source["source_record_id"]
        if not isinstance(source_id, str):
            raise TypeError("source_record_id must be a string")
        target_uuid = uuid5(NAMESPACE_URL, f"pvr:image-search-evaluation:{source_id}")
        members.append(
            {
                "case_id": case.id,
                "query": case.query,
                "normalized_query": normalize_text(case.query),
                "partition": partition,
                "component_sha256": component_by_case[case.id],
                "casting_family": {
                    "brand": normalize_text(case.expected_full_identity.brand),
                    "casting": normalize_text(case.expected_full_identity.casting),
                },
                "exact_identity": case.expected_full_identity.model_dump(mode="json"),
                "target_uuid": str(target_uuid),
                "evidence_event": source_id,
                "aliases": sorted(
                    {
                        str(value)
                        for value in (source.get("casting_name"), source.get("source_model_label"))
                        if isinstance(value, str) and value.strip()
                    }
                ),
            }
        )

    overlap_by_key = {
        ("normalized_query_duplicate" if namespace == "query" else namespace): len(
            group_values["ranker_train"][namespace]
            & group_values["ranker_selection"][namespace]
        )
        for namespace in ("family", "identity", "query", "alias", "evidence")
    }
    if any(overlap_by_key.values()):
        raise ValueError("family/evidence-safe partition leakage was detected")
    partition_counts = Counter(assignment.values())
    if (
        partition_counts["ranker_train"] < RANKER_TRAIN_MINIMUM
        or partition_counts["ranker_selection"] < RANKER_SELECTION_MINIMUM
    ):
        raise ValueError("ranker partitions do not satisfy minimum counts")

    local_body: dict[str, Any] = {
        "schema_version": SCHEMA_LOCAL_PARTITIONS,
        "version": VERSION,
        "authorization_sha256": authorization["authorization_sha256"],
        "partition_salt": PARTITION_SALT,
        "positive_parent": {
            "dataset_sha256": POSITIVE_DATASET_SHA256,
            "development_test_assignment_sha256": POSITIVE_SPLIT_SHA256,
        },
        "members": members,
        "no_match_existing_split": {
            "candidate_set_sha256": NO_MATCH_CANDIDATE_SET_SHA256,
            "assignment_sha256": NO_MATCH_SPLIT_SHA256,
            "calibration_fit_count": FIT_COUNT,
            "threshold_selection_count": SELECTION_COUNT,
            "ranker_use_allowed": False,
        },
    }
    local = {**local_body, "content_sha256": _content_sha256(local_body)}
    private_assignment_rows = [
        [
            hashlib.sha256(
                f"{PRIVATE_DIGEST_SALT}\0member\0{member['case_id']}".encode()
            ).hexdigest(),
            member["partition"],
            member["component_sha256"],
        ]
        for member in members
    ]
    public_body: dict[str, Any] = {
        "schema_version": SCHEMA_SPLIT_MANIFEST,
        "version": VERSION,
        "status": "ranker_partitions_frozen_calibration_positive_shortfall",
        "authorization_sha256": authorization["authorization_sha256"],
        "parent_bindings": {
            "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
            "positive_development_test_assignment_sha256": POSITIVE_SPLIT_SHA256,
            "catalog_sha256": CATALOG_SHA256,
            "no_match_candidate_set_sha256": NO_MATCH_CANDIDATE_SET_SHA256,
            "no_match_assignment_sha256": NO_MATCH_SPLIT_SHA256,
        },
        "deterministic_partition": {
            "algorithm": "connected_components_then_salted_component_order_v1",
            "salt_version": "drsp-t2-ranker-partitions-v1",
            "target_ranker_train_count": RANKER_TRAIN_TARGET,
            "minimum_ranker_train_count": RANKER_TRAIN_MINIMUM,
            "minimum_ranker_selection_count": RANKER_SELECTION_MINIMUM,
        },
        "aggregate_counts": {
            "admitted_positive_development": len(members),
            "ranker_train": partition_counts["ranker_train"],
            "ranker_selection": partition_counts["ranker_selection"],
            "connected_component_count": len(components),
            "largest_connected_component": max(len(component) for component in components),
            "permanently_excluded_positive_test": POSITIVE_TEST_COUNT,
            "permanently_excluded_negative_holdout": NEGATIVE_HOLDOUT_COUNT,
            "no_match_calibration_fit_unchanged": FIT_COUNT,
            "no_match_threshold_selection_unchanged": SELECTION_COUNT,
        },
        "component_size_distribution": {
            str(size): count for size, count in sorted(component_sizes.items())
        },
        "zero_overlap_audit": overlap_by_key,
        "private_assignment_sha256": hashlib.sha256(
            _canonical_bytes(private_assignment_rows)
        ).hexdigest(),
        "private_partition_artifact_sha256": _content_sha256(local),
        "calibration_readiness": {
            "catalog_absence_examples_available": FIT_COUNT + SELECTION_COUNT,
            "catalog_present_family_disjoint_examples_available": 0,
            "exact_correctness_calibration_ready": False,
            "shortfall": "new_family_disjoint_catalog_present_calibration_rows_required",
            "ranker_pool_work_may_continue_to_t3": True,
        },
        "guardrails": {
            "positive_test_adaptive_use": 0,
            "negative_holdout_adaptive_use": 0,
            "no_match_ranker_use": 0,
            "hard_negatives_mined": 0,
            "training_runs_started": 0,
            "calibration_fits_started": 0,
            "runtime_default_changed": False,
        },
    }
    public = {**public_body, "manifest_sha256": _content_sha256(public_body)}
    if _contains_public_row_level_data(public):
        raise ValueError("DRSP-T2 split manifest contains row-level output")
    return local, public


def _code_bindings(root: Path) -> dict[str, str]:
    return {str(path): _file_sha256(root / path) for path in CODE_PATHS}


def _pool_size_distribution(sizes: Sequence[int]) -> dict[str, int]:
    return {str(size): count for size, count in sorted(Counter(sizes).items())}


def _target_rrf_rank(target_uuid: str, candidates: Sequence[Any]) -> int | None:
    """Observe retrieval success without altering the query-only candidate sequence."""
    return next(
        (
            candidate.rrf_rank
            for candidate in candidates
            if candidate.canonical_uuid == target_uuid
        ),
        None,
    )


def _load_default_scorer(root: Path) -> PointwiseScorer:
    config_path = root / POINTWISE_CONFIG_PATH
    model_path = root / POINTWISE_MODEL_PATH
    _require_file(config_path, FROZEN_POINTWISE_CONFIG_SHA256, "generic pointwise config")
    _require_file(
        model_path / "manifest.json",
        FROZEN_POINTWISE_MANIFEST_SHA256,
        "generic pointwise manifest",
    )
    config = load_pointwise_model_config(config_path)
    validate_local_pointwise_model(config, model_path)
    return LocalPointwiseScorer.load(config, model_path)


def build_candidate_pools(
    root: Path,
    authorization: Mapping[str, Any],
    local_partitions: Mapping[str, Any],
    split_manifest: Mapping[str, Any],
    *,
    scorer: PointwiseScorer | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if dict(authorization) != build_authorization(root):
        raise ValueError("DRSP-T2 owner authorization is stale or out of scope")
    expected_local, expected_public = build_partitions(root, authorization)
    if dict(local_partitions) != expected_local or dict(split_manifest) != expected_public:
        raise ValueError("DRSP-T2 partition inputs are stale or tampered")

    records = load_source_records(root / CATALOG_PATH)
    catalog = build_evaluation_catalog(records)
    structured = StructuredRetriever(catalog)
    retrieval = CandidateRetrievalService(
        [
            SparseRetriever(catalog),
            DenseRetriever(catalog, HashingEmbedding(DENSE_DIMENSIONS)),
            structured,
        ],
        structured,
    )
    color_vocabulary = {item.product.color for item in catalog.products if item.product.color}
    series_vocabulary = {item.product.series for item in catalog.products if item.product.series}

    members = local_partitions.get("members")
    if not isinstance(members, list) or len(members) != POSITIVE_DEVELOPMENT_COUNT:
        raise ValueError("local partition membership is missing or incomplete")
    pending: list[tuple[dict[str, Any], tuple[Any, ...], tuple[str, ...]]] = []
    all_pairs: list[tuple[str, str]] = []
    for raw in members:
        if not isinstance(raw, dict):
            raise TypeError("local partition member must be an object")
        query = raw.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("local partition member query is invalid")
        signals = extract_signals(query, color_vocabulary, series_vocabulary)
        # Expected identity is intentionally unavailable to this call.  This is the
        # target-injection boundary: retrieval receives query-derived signals only.
        retrieved = retrieval.retrieve(signals, CANDIDATE_LIMIT)
        frozen = tuple(freeze_candidate(candidate) for candidate in retrieved)
        rendered = tuple(render_candidate_text(candidate.text) for candidate in frozen)
        all_pairs.extend((query, candidate_text) for candidate_text in rendered)
        pending.append((raw, frozen, rendered))

    active_scorer = scorer if scorer is not None else _load_default_scorer(root)
    scores = active_scorer.score_pairs(all_pairs)
    if len(scores) != len(all_pairs):
        raise ValueError("generic pointwise scorer returned an incomplete score vector")
    if any(not math.isfinite(score) for score in scores):
        raise ValueError("generic pointwise scorer returned a non-finite value")

    rows: list[dict[str, Any]] = []
    score_offset = 0
    retrieval_misses = 0
    sizes: list[int] = []
    per_partition: Counter[str] = Counter()
    target_injections = 0
    for raw, frozen, rendered in pending:
        row_scores = tuple(scores[score_offset : score_offset + len(frozen)])
        score_offset += len(frozen)
        ranked = rank_scores(frozen, row_scores)
        generic_rank_by_uuid = {
            item.canonical_uuid: item.rank for item in ranked
        }
        score_by_uuid = {
            candidate.canonical_uuid: score
            for candidate, score in zip(frozen, row_scores, strict=True)
        }
        target_uuid = raw.get("target_uuid")
        if not isinstance(target_uuid, str):
            raise TypeError("local target UUID is invalid")
        UUID(target_uuid)
        candidate_uuids = tuple(candidate.canonical_uuid for candidate in frozen)
        target_rrf_rank = _target_rrf_rank(target_uuid, frozen)
        if target_rrf_rank is None:
            retrieval_misses += 1
        partition = raw.get("partition")
        if partition not in {"ranker_train", "ranker_selection"}:
            raise ValueError("local member partition is invalid")
        per_partition[str(partition)] += 1
        sizes.append(len(frozen))
        rows.append(
            {
                "case_id": raw["case_id"],
                "partition": partition,
                "query": raw["query"],
                "target_uuid": target_uuid,
                "target_retrieved": target_rrf_rank is not None,
                "target_rrf_rank": target_rrf_rank,
                "target_generic_rank": generic_rank_by_uuid.get(target_uuid),
                "candidates": [
                    {
                        "canonical_uuid": candidate.canonical_uuid,
                        "canonical_id": candidate.canonical_id,
                        "rendered_text": candidate_text,
                        "rrf_rank": candidate.rrf_rank,
                        "rrf_score": candidate.rrf_score,
                        "source_ranks": dict(candidate.source_ranks),
                        "source_scores": dict(candidate.source_scores),
                        "structured_matches": list(candidate.structured_matches),
                        "structured_conflicts": list(candidate.structured_conflicts),
                        "generic_pointwise_score": score_by_uuid[candidate.canonical_uuid],
                        "generic_pointwise_rank": generic_rank_by_uuid[candidate.canonical_uuid],
                    }
                    for candidate, candidate_text in zip(frozen, rendered, strict=True)
                ],
                "retrieval_output_sha256": _content_sha256(candidate_uuids),
            }
        )

    if score_offset != len(scores):
        raise ValueError("generic score cursor did not consume the complete vector")
    if any(size > CANDIDATE_LIMIT for size in sizes):
        raise ValueError("candidate pool exceeds the frozen Top-25 limit")
    if target_injections:
        raise ValueError("target injection was detected")

    local_body: dict[str, Any] = {
        "schema_version": SCHEMA_LOCAL_POOLS,
        "version": VERSION,
        "authorization_sha256": authorization["authorization_sha256"],
        "private_partition_artifact_sha256": _content_sha256(local_partitions),
        "candidate_limit": CANDIDATE_LIMIT,
        "retrieval": {
            "sparse": "token-index-v1",
            "dense": f"hashing-v1:{DENSE_DIMENSIONS}",
            "structured": "structured-v1",
            "fusion": f"rrf:k={RRF_K}",
        },
        "generic_pointwise": {
            "model_id": POINTWISE_MODEL_ID,
            "revision": POINTWISE_REVISION,
            "config_sha256": FROZEN_POINTWISE_CONFIG_SHA256,
            "local_manifest_sha256": FROZEN_POINTWISE_MANIFEST_SHA256,
            "scorer_version": active_scorer.version,
            "score_semantics": "ranking_relevance_logit_not_probability_or_confidence",
        },
        "rows": rows,
    }
    local = {**local_body, "content_sha256": _content_sha256(local_body)}
    miss_rate = retrieval_misses / len(rows)
    public_body: dict[str, Any] = {
        "schema_version": SCHEMA_POOL_MANIFEST,
        "version": VERSION,
        "status": (
            "frozen_candidate_pools_ready_for_train_only_mining"
            if miss_rate <= 0.05
            else "retrieval_shortfall_blocks_train_only_mining"
        ),
        "authorization_sha256": authorization["authorization_sha256"],
        "split_manifest_sha256": split_manifest["manifest_sha256"],
        "bindings": {
            "catalog_sha256": CATALOG_SHA256,
            "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
            "generic_model_id": POINTWISE_MODEL_ID,
            "generic_model_revision": POINTWISE_REVISION,
            "generic_model_config_sha256": FROZEN_POINTWISE_CONFIG_SHA256,
            "generic_model_manifest_sha256": FROZEN_POINTWISE_MANIFEST_SHA256,
            "renderer": "render_candidate_text-v1",
            "renderer_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/neural_reranking.py"
            ),
            "code_sha256": _code_bindings(root),
        },
        "retrieval_contract": {
            "candidate_limit": CANDIDATE_LIMIT,
            "sparse": "token-index-v1",
            "dense": f"hashing-v1:{DENSE_DIMENSIONS}",
            "structured": "structured-v1",
            "fusion": f"rrf:k={RRF_K}",
            "target_injection_allowed": False,
            "same_pool_for_generic_and_future_domain_comparison": True,
        },
        "aggregate_counts": {
            "pool_count": len(rows),
            "ranker_train_pool_count": per_partition["ranker_train"],
            "ranker_selection_pool_count": per_partition["ranker_selection"],
            "retrieval_miss_count": retrieval_misses,
            "target_injection_count": target_injections,
            "positive_test_scored": 0,
            "negative_holdout_scored": 0,
            "no_match_ranker_scored": 0,
        },
        "pool_size": {
            "minimum": min(sizes),
            "maximum": max(sizes),
            "mean": sum(sizes) / len(sizes),
            "distribution": _pool_size_distribution(sizes),
        },
        "retrieval": {
            "miss_rate": miss_rate,
            "maximum_allowed_miss_rate": 0.05,
            "gate_passed": miss_rate <= 0.05,
        },
        "private_pool_artifact_sha256": _content_sha256(local),
        "guardrails": {
            "expected_target_passed_to_retriever": False,
            "hard_negatives_mined": 0,
            "model_training_runs": 0,
            "model_selection_runs": 0,
            "calibration_fits": 0,
            "fresh_final_reads": 0,
            "runtime_default_changed": False,
        },
        "next_allowed_action": (
            "DRSP-T3_train_only_mining_requires_separate_execution"
            if miss_rate <= 0.05
            else "stop_and_resolve_retrieval_shortfall_before_DRSP-T3"
        ),
    }
    public = {**public_body, "manifest_sha256": _content_sha256(public_body)}
    if _contains_public_row_level_data(public):
        raise ValueError("DRSP-T2 candidate-pool manifest contains row-level output")
    return local, public


def _validate_digest(payload: Mapping[str, Any], field: str, name: str) -> None:
    body = {key: value for key, value in payload.items() if key != field}
    if payload.get(field) != _content_sha256(body):
        raise ValueError(f"{name} checksum is stale")


def _write(path: Path, payload: object, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    path.chmod(mode)


def materialize(root: Path, *, scorer: PointwiseScorer | None = None) -> dict[str, Any]:
    paths = (
        root / AUTHORIZATION_PATH,
        root / SPLIT_MANIFEST_PATH,
        root / POOL_MANIFEST_PATH,
        root / LOCAL_PARTITIONS_PATH,
        root / LOCAL_POOLS_PATH,
    )
    if any(path.exists() for path in paths):
        raise FileExistsError("DRSP-T2 artifacts already exist")
    authorization = build_authorization(root)
    local_partitions, split_manifest = build_partitions(root, authorization)
    local_pools, pool_manifest = build_candidate_pools(
        root,
        authorization,
        local_partitions,
        split_manifest,
        scorer=scorer,
    )
    _write(root / LOCAL_PARTITIONS_PATH, local_partitions, 0o600)
    _write(root / LOCAL_POOLS_PATH, local_pools, 0o600)
    _write(root / AUTHORIZATION_PATH, authorization, 0o644)
    _write(root / SPLIT_MANIFEST_PATH, split_manifest, 0o644)
    _write(root / POOL_MANIFEST_PATH, pool_manifest, 0o644)
    return pool_manifest


def check(root: Path, *, require_local_artifacts: bool = True) -> dict[str, Any]:
    _validate_t1_chain(root)
    public_paths = (AUTHORIZATION_PATH, SPLIT_MANIFEST_PATH, POOL_MANIFEST_PATH)
    for relative in public_paths:
        path = root / relative
        if stat.S_IMODE(path.stat().st_mode) != 0o644:
            raise ValueError(f"{relative}: public artifact must use mode 0644")
    authorization = _load_object(root / AUTHORIZATION_PATH)
    split_manifest = _load_object(root / SPLIT_MANIFEST_PATH)
    pool_manifest = _load_object(root / POOL_MANIFEST_PATH)
    if authorization != build_authorization(root):
        raise ValueError("DRSP-T2 owner authorization is stale or tampered")
    _validate_digest(authorization, "authorization_sha256", "DRSP-T2 authorization")
    _validate_digest(split_manifest, "manifest_sha256", "DRSP-T2 split manifest")
    _validate_digest(pool_manifest, "manifest_sha256", "DRSP-T2 pool manifest")
    if any(
        _contains_public_row_level_data(payload)
        for payload in (authorization, split_manifest, pool_manifest)
    ):
        raise ValueError("DRSP-T2 public artifact contains row-level output")
    if require_local_artifacts:
        for relative in (LOCAL_PARTITIONS_PATH, LOCAL_POOLS_PATH):
            if stat.S_IMODE((root / relative).stat().st_mode) != 0o600:
                raise ValueError(f"{relative}: private artifact must use mode 0600")
        local_partitions = _load_object(root / LOCAL_PARTITIONS_PATH)
        local_pools = _load_object(root / LOCAL_POOLS_PATH)
        _validate_digest(local_partitions, "content_sha256", "DRSP-T2 local partitions")
        _validate_digest(local_pools, "content_sha256", "DRSP-T2 local pools")
        expected_local, expected_split = build_partitions(root, authorization)
        if local_partitions != expected_local or split_manifest != expected_split:
            raise ValueError("DRSP-T2 partition artifact drift detected")
        if split_manifest.get("private_partition_artifact_sha256") != _content_sha256(
            local_partitions
        ):
            raise ValueError("private partition binding changed")
        if pool_manifest.get("private_pool_artifact_sha256") != _content_sha256(local_pools):
            raise ValueError("private candidate-pool binding changed")
        rows = local_pools.get("rows")
        if not isinstance(rows, list) or len(rows) != POSITIVE_DEVELOPMENT_COUNT:
            raise ValueError("private candidate-pool count changed")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("candidates"), list):
                raise TypeError("private candidate-pool row is invalid")
            if len(row["candidates"]) > CANDIDATE_LIMIT:
                raise ValueError("private candidate-pool row exceeds Top-25")
        expected_pools, expected_pool_manifest = build_candidate_pools(
            root,
            authorization,
            local_partitions,
            split_manifest,
        )
        if local_pools != expected_pools or pool_manifest != expected_pool_manifest:
            raise ValueError("DRSP-T2 candidate-pool artifact drift detected")
    return pool_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize or validate DRSP-T2 partitions and frozen candidate pools"
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    parser.add_argument("--public-only", action="store_true")
    arguments = parser.parse_args()
    root = Path.cwd()
    if arguments.run:
        if not arguments.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        result = materialize(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if arguments.check:
        check(root, require_local_artifacts=not arguments.public_only)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
