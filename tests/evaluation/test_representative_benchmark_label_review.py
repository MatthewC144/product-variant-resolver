from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, cast

import pytest

from product_variant_resolver.representative_benchmark_governance_overlay import (
    LABEL_REFERENCES,
    materialize_governance_overlay,
)
from product_variant_resolver.representative_benchmark_governance_overlay import (
    OWNER_AUTHORIZATION_REFERENCE as GOVERNANCE_AUTHORIZATION_REFERENCE,
)
from product_variant_resolver.representative_benchmark_label_review import (
    AUTHORIZATION_REFERENCE,
    EVIDENCE_REFERENCE,
    MANIFEST_REFERENCE,
    PROPOSALS_REFERENCE,
    WORKSPACE_REFERENCE,
    LabelReviewError,
    build_label_review_artifacts,
    materialize_label_review,
    validate_materialized_label_review,
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
    Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json"),
)
PRIVATE_INPUTS = (
    PROJECTION_REFERENCE,
    QUERY_AUTHORIZATION_REFERENCE,
    AUTHORING_INPUT_REFERENCE,
    QUERY_PACK_REFERENCE,
    GOVERNANCE_AUTHORIZATION_REFERENCE,
    AUTHORIZATION_REFERENCE,
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
    os.chmod(root / PRIVATE_AUTHORING_DIRECTORY, 0o700)
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


def test_real_review_artifacts_are_deterministic_conservative_and_non_approving() -> None:
    first = build_label_review_artifacts(ROOT)
    second = build_label_review_artifacts(ROOT)
    evidence, proposals, manifest = first

    assert first == second
    assert len(evidence.packets) == len(proposals.proposals) == manifest.record_count == 60
    assert manifest.suggested_status_counts == {
        "ambiguous": 5,
        "held": 51,
        "matched": 0,
        "no_match": 4,
    }
    assert manifest.owner_approved_label_count == 0
    assert not manifest.labels_materialized
    assert not manifest.row_level_data_public
    assert all(not proposal.owner_decision_recorded for proposal in proposals.proposals)
    assert all(not proposal.score_eligible for proposal in proposals.proposals)


def test_materialization_is_private_canonical_and_replayable(isolated_root: Path) -> None:
    assert materialize_label_review(isolated_root) == "created"
    assert stat.S_IMODE((isolated_root / WORKSPACE_REFERENCE).stat().st_mode) == 0o700
    assert stat.S_IMODE((isolated_root / EVIDENCE_REFERENCE).stat().st_mode) == 0o600
    assert stat.S_IMODE((isolated_root / PROPOSALS_REFERENCE).stat().st_mode) == 0o600
    assert stat.S_IMODE((isolated_root / MANIFEST_REFERENCE).stat().st_mode) == 0o644
    assert materialize_label_review(isolated_root) == "unchanged"
    assert materialize_label_review(isolated_root, check=True) == "unchanged"


def test_materialized_real_review_matches_the_builder() -> None:
    expected = build_label_review_artifacts(ROOT)
    assert validate_materialized_label_review(ROOT) == expected


def test_one_private_case_is_ambiguous_across_three_admitted_releases() -> None:
    evidence, proposals, _manifest = build_label_review_artifacts(ROOT)
    packets = [
        packet for packet in evidence.packets if packet.admitted_authority_candidate_count > 0
    ]
    assert len(packets) == 1
    packet = packets[0]
    proposal = next(
        proposal for proposal in proposals.proposals if proposal.case_id == packet.case_id
    )

    assert packet.catalog_candidate_count == packet.admitted_authority_candidate_count == 3
    assert all(candidate.authority_admitted for candidate in packet.catalog_candidates)
    assert proposal.suggested_expected_status == "ambiguous"
    assert proposal.suggested_canonical_uuid is None
    assert proposal.suggested_authority_id is None


def test_public_manifest_contains_no_row_level_query_label_or_owner_response() -> None:
    payload = _read(ROOT / MANIFEST_REFERENCE)
    forbidden = {
        "authorization_text",
        "case_id",
        "canonical_uuid",
        "expected_status",
        "proposal_basis",
        "query",
        "source_record_ref",
    }
    assert not forbidden & _collect_keys(payload)


def test_authorization_tamper_fails_closed(isolated_root: Path) -> None:
    authorization_path = isolated_root / AUTHORIZATION_REFERENCE
    payload = _read(authorization_path)
    payload["authorization_text_sha256"] = "0" * 64
    authorization_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(authorization_path, 0o600)

    with pytest.raises(ValueError):
        build_label_review_artifacts(isolated_root)


def test_partial_outputs_fail_without_overwrite(isolated_root: Path) -> None:
    workspace = isolated_root / WORKSPACE_REFERENCE
    workspace.mkdir(mode=0o700)
    evidence_path = isolated_root / EVIDENCE_REFERENCE
    evidence_path.write_text("{}\n", encoding="utf-8")
    os.chmod(evidence_path, 0o600)

    with pytest.raises(LabelReviewError, match="partial"):
        materialize_label_review(isolated_root)
    assert evidence_path.read_text(encoding="utf-8") == "{}\n"


def test_downstream_authorization_does_not_break_overlay_replay() -> None:
    assert materialize_governance_overlay(ROOT, check=True) == "unchanged"


def test_no_label_split_or_evaluation_artifact_was_created() -> None:
    assert not any((ROOT / reference).exists() for reference in LABEL_REFERENCES)
    assert not (ROOT / RHB / "benchmark-manifest.json").exists()


def test_module_has_no_forbidden_data_or_runtime_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_label_review.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "human_labeled_names",
        "ResolverService",
        "import requests",
        "import selenium",
        "validate_labels(",
        "validate_split(",
        "pointwise",
        "listwise",
    )
    assert all(token not in source for token in forbidden)
