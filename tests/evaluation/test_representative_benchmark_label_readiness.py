from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from product_variant_resolver.representative_benchmark_governance_overlay import (
    OWNER_AUTHORIZATION_REFERENCE as GOVERNANCE_AUTHORIZATION_REFERENCE,
)
from product_variant_resolver.representative_benchmark_label_readiness import (
    LABEL_REFERENCES,
    LabelReadinessError,
    build_rhb_t6_label_readiness,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    AUTHORING_INPUT_REFERENCE,
    OWNER_AUTHORIZATION_REFERENCE,
    PROJECTION_REFERENCE,
    QUERY_PACK_REFERENCE,
)

ROOT = Path(__file__).resolve().parents[2]
RHB = Path("data/evaluation/representative-hard-benchmark-v1")
CLI = ROOT / "scripts/validate_representative_hard_benchmark_label_readiness.py"
PUBLIC_INPUTS = (
    Path(".gitignore"),
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
    OWNER_AUTHORIZATION_REFERENCE,
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


def test_real_readiness_is_deterministic_read_only_and_ready_for_separate_gate() -> None:
    watched = [ROOT / reference for reference in LABEL_REFERENCES]
    before = {path: path.exists() for path in watched}

    first = build_rhb_t6_label_readiness(ROOT)
    second = build_rhb_t6_label_readiness(ROOT)

    assert first == second
    assert first.status == "ready_for_separate_owner_authorization"
    assert first.query_pack_record_count == 60
    assert first.query_pack_core_validator_passed
    assert not first.query_pack_representative_pilot
    assert first.query_source_ids == ["human-labeled-real-noisy-v1"]
    assert first.query_source_allowed_label_statuses == {
        "human-labeled-real-noisy-v1": ["ambiguous", "no_match"]
    }
    assert first.maximum_source_permitted_matched_count == 0
    assert first.maximum_overlay_permitted_matched_count == 20
    assert first.matched_permission_shortfall == 0
    assert first.canonical_authority_record_count == 20
    assert not first.canonical_authority_t1_t3_compatible
    assert first.canonical_authority_admitted_by_overlay
    assert first.matched_labels_admitted_by_overlay
    assert first.incompatible_authority_source_ids == ["fandom-hot-wheels-2025-pilot-r790665-v1"]
    assert first.provisional_challenge_shortfall_total == 16
    assert first.owner_gate_requestable
    assert first.blockers == []
    assert first.next_allowed_action == "request_separate_rhb_t6_label_authoring_owner_gate"
    assert not first.rhb_t6_authorized
    assert {path: path.exists() for path in watched} == before


def test_cli_emits_the_same_hash_bound_report() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    expected = build_rhb_t6_label_readiness(ROOT)
    assert payload == expected.model_dump(mode="json")
    unhashed = dict(payload)
    digest = unhashed.pop("readiness_sha256")
    canonical = json.dumps(
        unhashed, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": ")
    )
    assert digest == hashlib.sha256(f"{canonical}\n".encode()).hexdigest()


def test_premature_label_artifact_fails_closed(isolated_root: Path) -> None:
    label_path = isolated_root / LABEL_REFERENCES[0]
    label_path.write_text("{}\n", encoding="utf-8")
    os.chmod(label_path, 0o600)

    with pytest.raises(LabelReadinessError, match="label artifacts already exist"):
        build_rhb_t6_label_readiness(isolated_root)


def test_query_manifest_tamper_fails_closed(isolated_root: Path) -> None:
    manifest_path = isolated_root / RHB / "query-pack-manifest.json"
    payload = _read(manifest_path)
    payload["record_count"] = 59
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        build_rhb_t6_label_readiness(isolated_root)


def test_authority_tamper_fails_closed(isolated_root: Path) -> None:
    authority_path = isolated_root / RHB / "canonical-authority-reaudit-v1.json"
    payload = _read(authority_path)
    payload["records"][0]["review_reason"] = "tampered"
    authority_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(LabelReadinessError, match="authority checksum drift"):
        build_rhb_t6_label_readiness(isolated_root)


def test_readiness_has_no_resolver_network_or_label_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_label_readiness.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import selenium",
        "import fastapi",
        "ResolverService",
        ".resolve(",
        "validate_labels(",
    )
    assert all(token not in source for token in forbidden)
