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

from product_variant_resolver.representative_benchmark import (
    CanonicalAuthorityArtifact,
    ContractError,
    RhbT6GovernanceOverlay,
    validate_canonical_authority,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_governance_overlay import (
    OVERLAY_REFERENCE,
    GovernanceOverlayError,
    build_governance_overlay,
    materialize_governance_overlay,
)
from product_variant_resolver.representative_benchmark_governance_overlay import (
    OWNER_AUTHORIZATION_REFERENCE as GOVERNANCE_AUTHORIZATION_REFERENCE,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    AUTHORING_INPUT_REFERENCE,
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
    Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json"),
)
PRIVATE_INPUTS = (
    PROJECTION_REFERENCE,
    QUERY_AUTHORIZATION_REFERENCE,
    AUTHORING_INPUT_REFERENCE,
    QUERY_PACK_REFERENCE,
    GOVERNANCE_AUTHORIZATION_REFERENCE,
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


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested_key for nested in value.values() for nested_key in _collect_keys(nested)
        }
    if isinstance(value, list):
        return {nested_key for nested in value for nested_key in _collect_keys(nested)}
    return set()


def test_real_overlay_is_deterministic_narrow_and_non_authorizing() -> None:
    first = build_governance_overlay(ROOT)
    second = build_governance_overlay(ROOT)

    assert first == second
    assert first.status == "active_for_bound_artifacts"
    assert first.query_label_admission.query_pack_sha256 == (
        "97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a"
    )
    assert first.query_label_admission.maximum_matched_labels == 20
    assert first.authority_bundle_admission.authority_sha256 == (
        "72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117"
    )
    assert len(first.authority_bundle_admission.authority_record_ids) == 20
    assert not first.authority_bundle_admission.source_wide_exact_authority_promotion
    assert not first.authority_bundle_admission.manufacturer_certification_claimed
    assert not first.authority_bundle_admission.color_or_edition_newly_verified
    assert not first.rhb_t6_label_authoring_authorized
    assert not first.rhb_t7_authorized
    assert not first.resolver_evaluation_authorized


def test_materialization_is_canonical_and_replays(isolated_root: Path) -> None:
    assert materialize_governance_overlay(isolated_root) == "created"
    overlay_path = isolated_root / OVERLAY_REFERENCE
    assert stat.S_IMODE(overlay_path.stat().st_mode) == 0o644
    assert materialize_governance_overlay(isolated_root) == "unchanged"
    assert materialize_governance_overlay(isolated_root, check=True) == "unchanged"


def test_materialized_real_overlay_matches_builder() -> None:
    actual = RhbT6GovernanceOverlay.model_validate(_read(ROOT / OVERLAY_REFERENCE))
    assert actual == build_governance_overlay(ROOT)


def test_overlay_admits_only_the_bound_authority_bundle() -> None:
    inventory_payload = _read(ROOT / RHB / "source-inventory.json")
    inventory_manifest_payload = _read(ROOT / RHB / "source-inventory-manifest.json")
    decisions_payload = _read(ROOT / RHB / "source-decisions.json")
    wiki_payload = _read(ROOT / "data/external/hot-wheels-wiki/pilot-2025/normalized.json")
    catalog_payload = _read(ROOT / "data/catalog.json")
    authority_payload = _read(ROOT / RHB / "canonical-authority-reaudit-v1.json")
    inventory, _manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    authority = CanonicalAuthorityArtifact.model_validate(authority_payload)

    with pytest.raises(ContractError, match="lacks typed canonical_authority permission"):
        validate_canonical_authority(
            authority_payload,
            inventory=inventory,
            catalog_payload=catalog_payload,
            source_decisions=decisions,
        )

    validated = validate_canonical_authority(
        authority_payload,
        inventory=inventory,
        catalog_payload=catalog_payload,
        source_decisions=decisions,
        governance_overlay=build_governance_overlay(ROOT),
    )
    assert validated == authority


def test_public_overlay_contains_no_owner_response_query_or_label_rows() -> None:
    payload = _read(ROOT / OVERLAY_REFERENCE)
    forbidden_keys = {
        "authorization_text",
        "owner_response",
        "query",
        "query_text",
        "source_record_ref",
        "label_records",
        "expected_status",
        "expected_canonical_uuid",
    }
    assert not forbidden_keys & _collect_keys(payload)


def test_overlay_cannot_widen_authority_or_enable_later_gates() -> None:
    payload = build_governance_overlay(ROOT).model_dump(mode="json")
    payload["authority_bundle_admission"]["source_wide_exact_authority_promotion"] = True
    with pytest.raises(ValidationError):
        RhbT6GovernanceOverlay.model_validate(payload)

    payload = build_governance_overlay(ROOT).model_dump(mode="json")
    payload["rhb_t6_label_authoring_authorized"] = True
    with pytest.raises(ValidationError):
        RhbT6GovernanceOverlay.model_validate(payload)


def test_private_owner_authorization_tamper_fails_closed(isolated_root: Path) -> None:
    authorization_path = isolated_root / GOVERNANCE_AUTHORIZATION_REFERENCE
    payload = _read(authorization_path)
    tampered = copy.deepcopy(payload)
    tampered["authorization_text_sha256"] = "0" * 64
    authorization_path.write_text(json.dumps(tampered), encoding="utf-8")
    os.chmod(authorization_path, 0o600)

    with pytest.raises((GovernanceOverlayError, ValidationError, ValueError)):
        build_governance_overlay(isolated_root)


def test_proposal_parent_tamper_fails_closed(isolated_root: Path) -> None:
    proposal_path = isolated_root / RHB / "rhb-t6-governance-repair-proposal.json"
    payload = _read(proposal_path)
    payload["owner_decision_required"] = False
    proposal_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises((GovernanceOverlayError, ValidationError, ValueError)):
        build_governance_overlay(isolated_root)


def test_module_has_no_label_resolver_or_network_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_governance_overlay.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import selenium",
        "ResolverService",
        "validate_labels(",
        '"labels":',
    )
    assert all(token not in source for token in forbidden)
