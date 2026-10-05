from __future__ import annotations

import copy
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from product_variant_resolver.representative_benchmark_governance_repair import (
    PROHIBITED_ACTIONS,
    PROPOSAL_REFERENCE,
    GovernanceRepairError,
    GovernanceRepairProposal,
    build_governance_repair_proposal,
    materialize_governance_repair_proposal,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    AUTHORING_INPUT_REFERENCE,
    OWNER_AUTHORIZATION_REFERENCE,
    PROJECTION_REFERENCE,
    QUERY_PACK_REFERENCE,
)

ROOT = Path(__file__).resolve().parents[2]
RHB = Path("data/evaluation/representative-hard-benchmark-v1")
PUBLIC_INPUTS = (
    Path(".gitignore"),
    RHB / "source-inventory.json",
    RHB / "source-inventory-manifest.json",
    RHB / "source-decisions.json",
    RHB / "query-authoring-source-manifest.json",
    RHB / "query-pack-manifest.json",
    RHB / "canonical-authority-reaudit-v1.json",
    RHB / "canonical-authority-reaudit-manifest-v1.json",
    Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json"),
)
PRIVATE_INPUTS = (
    PROJECTION_REFERENCE,
    OWNER_AUTHORIZATION_REFERENCE,
    AUTHORING_INPUT_REFERENCE,
    QUERY_PACK_REFERENCE,
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
    os.chmod(root / PROJECTION_REFERENCE.parent, 0o700)
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_real_proposal_is_deterministic_narrow_and_non_authorizing() -> None:
    first = build_governance_repair_proposal(ROOT)
    second = build_governance_repair_proposal(ROOT)

    assert first == second
    assert first.status == "awaiting_owner_decision"
    assert first.frozen_t1_t3_preserved_without_overwrite
    assert first.query_label_admission.query_pack_record_count == 60
    assert first.query_label_admission.current_allowed_statuses == [
        "ambiguous",
        "no_match",
    ]
    assert first.query_label_admission.proposed_additional_status == "matched"
    assert first.query_label_admission.human_source_remains_ineligible_for_exact_authority
    assert first.authority_bundle_admission.authority_record_count == 20
    assert not first.authority_bundle_admission.source_wide_exact_authority_promotion
    assert not first.authority_bundle_admission.manufacturer_certification_claimed
    assert first.challenge_review_carry_forward.provisional_shortfall_total == 16
    assert first.prohibited_actions == PROHIBITED_ACTIONS
    assert first.proposal_only and first.owner_decision_required
    assert not first.governance_overlay_materialized
    assert not first.rhb_t6_authorized


def test_materialization_is_canonical_and_replays(isolated_root: Path) -> None:
    assert materialize_governance_repair_proposal(isolated_root) == "created"
    proposal_path = isolated_root / PROPOSAL_REFERENCE
    assert stat.S_IMODE(proposal_path.stat().st_mode) == 0o644
    assert materialize_governance_repair_proposal(isolated_root) == "unchanged"
    assert materialize_governance_repair_proposal(isolated_root, check=True) == "unchanged"


def test_materialized_real_proposal_matches_the_builder() -> None:
    payload = _read(ROOT / PROPOSAL_REFERENCE)
    actual = GovernanceRepairProposal.model_validate(payload)
    assert actual == build_governance_repair_proposal(ROOT)


def test_proposal_cannot_authorize_or_widen_the_source() -> None:
    payload = build_governance_repair_proposal(ROOT).model_dump(mode="json")
    payload["rhb_t6_authorized"] = True
    with pytest.raises(ValidationError):
        GovernanceRepairProposal.model_validate(payload)

    payload = build_governance_repair_proposal(ROOT).model_dump(mode="json")
    payload["authority_bundle_admission"]["source_wide_exact_authority_promotion"] = True
    with pytest.raises(ValidationError):
        GovernanceRepairProposal.model_validate(payload)


def test_public_proposal_contains_no_row_level_query_label_or_owner_response() -> None:
    payload = build_governance_repair_proposal(ROOT).model_dump(mode="json")
    forbidden_keys = {
        "query",
        "query_text",
        "source_record_ref",
        "owner_response",
        "authorization_text",
        "label_records",
        "expected_status",
        "expected_canonical_uuid",
    }

    def collect_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                nested_key for nested in value.values() for nested_key in collect_keys(nested)
            }
        if isinstance(value, list):
            return {nested_key for nested in value for nested_key in collect_keys(nested)}
        return set()

    assert not forbidden_keys & collect_keys(payload)


def test_parent_drift_fails_closed(isolated_root: Path) -> None:
    query_manifest_path = isolated_root / RHB / "query-pack-manifest.json"
    payload = _read(query_manifest_path)
    payload["non_sensitive_summary"] = "tampered"
    query_manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises((GovernanceRepairError, ValueError)):
        build_governance_repair_proposal(isolated_root)


def test_materialized_proposal_tamper_fails_closed(isolated_root: Path) -> None:
    assert materialize_governance_repair_proposal(isolated_root) == "created"
    proposal_path = isolated_root / PROPOSAL_REFERENCE
    payload = _read(proposal_path)
    tampered = copy.deepcopy(payload)
    tampered["proposal_only"] = False
    proposal_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises((GovernanceRepairError, ValidationError, ValueError)):
        materialize_governance_repair_proposal(isolated_root, check=True)


def test_module_has_no_overlay_label_resolver_or_network_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_governance_repair.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import selenium",
        "ResolverService",
        "validate_labels(",
        "labels.json",
        "governance-overlay.json",
    )
    assert all(token not in source for token in forbidden)
