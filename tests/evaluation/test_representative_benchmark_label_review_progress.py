from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, cast

import pytest

from product_variant_resolver.representative_benchmark_governance_overlay import (
    OWNER_AUTHORIZATION_REFERENCE as GOVERNANCE_AUTHORIZATION_REFERENCE,
)
from product_variant_resolver.representative_benchmark_label_review import (
    AUTHORIZATION_REFERENCE,
    EVIDENCE_REFERENCE,
    MANIFEST_REFERENCE,
    PROPOSALS_REFERENCE,
    WORKSPACE_REFERENCE,
)
from product_variant_resolver.representative_benchmark_label_review_progress import (
    APPROVED_BATCHES,
    BATCH_01_REFERENCE,
    BATCH_02_REFERENCE,
    DECISIONS_DIRECTORY,
    PROGRESS_REFERENCE,
    build_review_progress,
    materialize_review_progress,
    validate_materialized_review_progress,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    AUTHORING_INPUT_REFERENCE,
    PRIVATE_AUTHORING_DIRECTORY,
    PROJECTION_REFERENCE,
    QUERY_PACK_REFERENCE,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    OWNER_AUTHORIZATION_REFERENCE as QUERY_AUTHORIZATION_REFERENCE,
)

ROOT = Path(__file__).resolve().parents[2]
RHB = Path("data/evaluation/representative-hard-benchmark-v1")
PUBLIC_INPUTS = (
    Path(".gitignore"),
    Path("data/catalog.json"),
    RHB / "source-inventory.json",
    RHB / "source-inventory-manifest.json",
    RHB / "source-decisions.json",
    RHB / "query-authoring-source-manifest.json",
    RHB / "query-pack-manifest.json",
    RHB / "canonical-authority-reaudit-v1.json",
    RHB / "canonical-authority-reaudit-manifest-v1.json",
    RHB / "rhb-t6-governance-repair-proposal.json",
    RHB / "rhb-t6-governance-overlay-v1.json",
    MANIFEST_REFERENCE,
    Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json"),
)
PRIVATE_INPUTS = (
    PROJECTION_REFERENCE,
    QUERY_AUTHORIZATION_REFERENCE,
    AUTHORING_INPUT_REFERENCE,
    QUERY_PACK_REFERENCE,
    GOVERNANCE_AUTHORIZATION_REFERENCE,
    AUTHORIZATION_REFERENCE,
    EVIDENCE_REFERENCE,
    PROPOSALS_REFERENCE,
    BATCH_01_REFERENCE,
    BATCH_02_REFERENCE,
)


def _copy(root: Path, reference: Path) -> None:
    target = root / reference
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / reference, target)
    os.chmod(target, stat.S_IMODE((ROOT / reference).stat().st_mode))


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for reference in (*PUBLIC_INPUTS, *PRIVATE_INPUTS):
        _copy(root, reference)
    for reference in (PRIVATE_AUTHORING_DIRECTORY, WORKSPACE_REFERENCE, DECISIONS_DIRECTORY):
        os.chmod(root / reference, 0o700)
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key for nested in value.values() for nested_key in _collect_keys(nested)
        }
    if isinstance(value, list):
        return {nested_key for nested in value for nested_key in _collect_keys(nested)}
    return set()


def test_real_progress_is_deterministic_aggregate_only_and_non_materializing() -> None:
    first = build_review_progress(ROOT)
    second = build_review_progress(ROOT)

    assert first == second
    assert first.decision_batch_count == first.latest_batch_number == 2
    assert first.owner_reviewed_case_count == 20
    assert first.owner_approved_decision_count == 1
    assert first.owner_held_decision_count == 19
    assert first.remaining_staged_count == 40
    assert first.approved_status_counts == {"ambiguous": 0, "matched": 0, "no_match": 1}
    assert first.verified_challenge_tag_count == first.matched_approved_count == 0
    assert not first.labels_materialized
    assert not first.row_level_data_public
    assert first.next_allowed_action == "present_rhb_t6_review_batch_03"


def test_materialization_is_canonical_and_replayable(isolated_root: Path) -> None:
    assert materialize_review_progress(isolated_root) == "created"
    path = isolated_root / PROGRESS_REFERENCE
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert materialize_review_progress(isolated_root) == "unchanged"
    assert materialize_review_progress(isolated_root, check=True) == "unchanged"


def test_materialization_only_append_updates_a_valid_prefix(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = "product_variant_resolver.representative_benchmark_label_review_progress"
    monkeypatch.setattr(f"{module}.APPROVED_BATCHES", APPROVED_BATCHES[:1])
    assert materialize_review_progress(isolated_root) == "created"

    monkeypatch.setattr(f"{module}.APPROVED_BATCHES", APPROVED_BATCHES)
    assert materialize_review_progress(isolated_root) == "updated"
    assert validate_materialized_review_progress(isolated_root).decision_batch_count == 2


def test_materialized_real_progress_matches_private_events() -> None:
    assert validate_materialized_review_progress(ROOT) == build_review_progress(ROOT)


def test_public_progress_contains_no_row_level_decision_or_owner_response() -> None:
    payload = _read(ROOT / PROGRESS_REFERENCE)
    forbidden = {
        "authorization_text",
        "case_decisions",
        "case_id",
        "canonical_uuid",
        "expected_status",
        "owner_response",
        "query",
        "review_reason_code",
        "source_record_ref",
    }
    assert not forbidden & _collect_keys(payload)


def test_private_batch_tamper_fails_closed(isolated_root: Path) -> None:
    path = isolated_root / BATCH_01_REFERENCE
    payload = _read(path)
    payload["owner_response_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)

    with pytest.raises(ValueError):
        build_review_progress(isolated_root)


def test_no_label_or_split_artifact_is_materialized() -> None:
    forbidden = (
        RHB / "labels-manifest.json",
        RHB / "benchmark-manifest.json",
        PRIVATE_AUTHORING_DIRECTORY / "labels.json",
        PRIVATE_AUTHORING_DIRECTORY / "held-labels.json",
    )
    assert not any((ROOT / reference).exists() for reference in forbidden)


def test_progress_module_has_no_resolver_split_or_scoring_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_label_review_progress.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "ResolverService",
        "import requests",
        "import selenium",
        "validate_labels(",
        "validate_split(",
        "score_results(",
    )
    assert all(token not in source for token in forbidden)
