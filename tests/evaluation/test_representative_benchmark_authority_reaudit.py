from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import product_variant_resolver.representative_benchmark_reaudit as reaudit
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)
from product_variant_resolver.representative_benchmark import CanonicalAuthorityArtifact
from product_variant_resolver.representative_benchmark_reaudit import (
    CAR_T6_AUTHORIZATION_REFERENCE,
    HISTORICAL_AUTHORITY_REFERENCE,
    HISTORICAL_MANIFEST_REFERENCE,
    REAUDIT_AUTHORITY_REFERENCE,
    REAUDIT_MANIFEST_REFERENCE,
    CarT6Authorization,
    CarT6ReauditManifest,
    build_car_t6_readiness,
    run_car_t6_reaudit,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "build_representative_hard_benchmark_authority_reaudit.py"
AUTHORIZED_RESPONSE = (
    "TEST-ONLY authorization for CAR-T6 versioned RHB-T4 re-audit; this does not authorize "
    "RHB-T5 and does not create query pack or labels."
)
AUTHORIZED_AT = datetime(2026, 10, 4, 16, 0, tzinfo=UTC)


@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "specs", root / "specs")
    shutil.copyfile(ROOT / ".gitignore", root / ".gitignore")
    private = root / "data/authority-review/canonical-authority-review-v1/local-authority-review-v1"
    os.chmod(private, 0o700)
    for path in private.iterdir():
        if path.is_file():
            os.chmod(path, 0o600)
    for reference in (
        CAR_T6_AUTHORIZATION_REFERENCE,
        REAUDIT_AUTHORITY_REFERENCE,
        REAUDIT_MANIFEST_REFERENCE,
    ):
        (root / reference).unlink(missing_ok=True)
    return root


def _read(root: Path, reference: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((root / reference).read_text(encoding="utf-8")))


def _run(root: Path, *, check: bool = False) -> str:
    return run_car_t6_reaudit(
        root,
        owner_response_verbatim=AUTHORIZED_RESPONSE,
        authorized_car_t6_owner_response=AUTHORIZED_RESPONSE,
        authorized_at=None if check else AUTHORIZED_AT,
        check=check,
    )


def _outputs_absent(root: Path) -> bool:
    return all(
        not (root / reference).exists()
        for reference in (
            CAR_T6_AUTHORIZATION_REFERENCE,
            REAUDIT_AUTHORITY_REFERENCE,
            REAUDIT_MANIFEST_REFERENCE,
        )
    )


def test_checked_in_reaudit_is_publicly_verifiable_without_private_owner_text() -> None:
    authority_raw = (ROOT / REAUDIT_AUTHORITY_REFERENCE).read_bytes()
    manifest_raw = (ROOT / REAUDIT_MANIFEST_REFERENCE).read_bytes()
    authority = CanonicalAuthorityArtifact.model_validate(_read(ROOT, REAUDIT_AUTHORITY_REFERENCE))
    manifest = CarT6ReauditManifest.model_validate(_read(ROOT, REAUDIT_MANIFEST_REFERENCE))

    assert len(authority.records) == 20
    assert len({record.canonical_uuid for record in authority.records}) == 20
    assert manifest.authority_sha256 == content_sha256(authority.model_dump(mode="json"))
    assert manifest.approved_exact_variant_count == 20
    assert manifest.qualifying_family_count == 7
    assert manifest.thresholds.exact_variant_shortfall == 0
    assert manifest.thresholds.qualifying_family_shortfall == 0
    assert (
        manifest.historical_rhb_t4.authority_sha256
        == hashlib.sha256((ROOT / HISTORICAL_AUTHORITY_REFERENCE).read_bytes()).hexdigest()
    )
    assert (
        manifest.historical_rhb_t4.manifest_sha256
        == hashlib.sha256((ROOT / HISTORICAL_MANIFEST_REFERENCE).read_bytes()).hexdigest()
    )
    assert manifest.historical_rhb_t4.preserved_without_overwrite
    assert manifest.next_allowed_step == "owner_gate_rhb_t5_separate_authorization_required"
    assert not manifest.rhb_t5_authorized
    assert AUTHORIZED_RESPONSE.encode() not in authority_raw + manifest_raw


def test_readiness_reaudits_car_t5f_without_writing_or_changing_history(
    isolated_root: Path,
) -> None:
    historical = {
        reference: (isolated_root / reference).read_bytes()
        for reference in (HISTORICAL_AUTHORITY_REFERENCE, HISTORICAL_MANIFEST_REFERENCE)
    }

    readiness = build_car_t6_readiness(isolated_root)

    assert readiness.status == "ready_for_separate_owner_authorization"
    assert readiness.historical_gate_result == "blocked_insufficient_exact_authority"
    assert readiness.historical_checkpoint_preserved
    assert readiness.car_t5f_gate_result == "eligible_for_rhb_t4_reaudit"
    assert readiness.proposed_reaudit_gate_result == "passed_exact_authority_gate"
    assert readiness.approved_exact_variant_count == 20
    assert readiness.qualifying_family_count == 7
    assert readiness.exact_variant_shortfall == 0
    assert readiness.qualifying_family_shortfall == 0
    assert not readiness.resolver_output_consulted
    assert not readiness.benchmark_labels_consulted
    assert readiness.network_requests == 0
    assert not readiness.rhb_t5_authorized
    assert _outputs_absent(isolated_root)
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in historical
    } == historical


def test_generic_continuation_and_mismatched_response_fail_closed(
    isolated_root: Path,
) -> None:
    with pytest.raises(AuthorityContractError, match="fresh explicit"):
        run_car_t6_reaudit(
            isolated_root,
            owner_response_verbatim="繼續下一步",
            authorized_car_t6_owner_response="繼續下一步",
            authorized_at=AUTHORIZED_AT,
        )
    with pytest.raises(AuthorityContractError, match="differs"):
        run_car_t6_reaudit(
            isolated_root,
            owner_response_verbatim=AUTHORIZED_RESPONSE,
            authorized_car_t6_owner_response=f"{AUTHORIZED_RESPONSE} changed",
            authorized_at=AUTHORIZED_AT,
        )
    assert _outputs_absent(isolated_root)


def test_materializes_versioned_reaudit_and_replays_without_overwriting_history(
    isolated_root: Path,
) -> None:
    historical = {
        reference: (isolated_root / reference).read_bytes()
        for reference in (HISTORICAL_AUTHORITY_REFERENCE, HISTORICAL_MANIFEST_REFERENCE)
    }

    assert _run(isolated_root) == "created"
    first = {
        reference: (isolated_root / reference).read_bytes()
        for reference in (
            CAR_T6_AUTHORIZATION_REFERENCE,
            REAUDIT_AUTHORITY_REFERENCE,
            REAUDIT_MANIFEST_REFERENCE,
        )
    }
    assert _run(isolated_root) == "unchanged"
    assert _run(isolated_root, check=True) == "unchanged"
    assert {reference: (isolated_root / reference).read_bytes() for reference in first} == first
    assert {
        reference: (isolated_root / reference).read_bytes() for reference in historical
    } == historical

    authorization = CarT6Authorization.model_validate(
        _read(isolated_root, CAR_T6_AUTHORIZATION_REFERENCE)
    )
    authority = CanonicalAuthorityArtifact.model_validate(
        _read(isolated_root, REAUDIT_AUTHORITY_REFERENCE)
    )
    manifest = CarT6ReauditManifest.model_validate(_read(isolated_root, REAUDIT_MANIFEST_REFERENCE))
    assert authorization.gate == "CAR-T6"
    assert len(authority.records) == 20
    assert len({record.canonical_uuid for record in authority.records}) == 20
    assert all(record.status.value == "approved_exact" for record in authority.records)
    assert manifest.gate_result == "passed_exact_authority_gate"
    assert manifest.approved_exact_variant_count == 20
    assert manifest.qualifying_family_count == 7
    assert manifest.thresholds.exact_variant_shortfall == 0
    assert manifest.thresholds.qualifying_family_shortfall == 0
    assert manifest.historical_rhb_t4.preserved_without_overwrite
    assert manifest.next_allowed_step == "owner_gate_rhb_t5_separate_authorization_required"
    assert not manifest.rhb_t5_authorized
    assert AUTHORIZED_RESPONSE.encode() not in (
        first[REAUDIT_AUTHORITY_REFERENCE] + first[REAUDIT_MANIFEST_REFERENCE]
    )
    assert (isolated_root / CAR_T6_AUTHORIZATION_REFERENCE).stat().st_mode & 0o777 == 0o600
    assert (isolated_root / REAUDIT_AUTHORITY_REFERENCE).stat().st_mode & 0o777 == 0o644
    assert (isolated_root / REAUDIT_MANIFEST_REFERENCE).stat().st_mode & 0o777 == 0o644
    with pytest.raises(AuthorityContractError, match="already materialized"):
        build_car_t6_readiness(isolated_root)


def test_tampered_car_t5f_input_blocks_reaudit_without_outputs(isolated_root: Path) -> None:
    catalog = isolated_root / reaudit.CATALOG_REFERENCE
    payload = _read(isolated_root, reaudit.CATALOG_REFERENCE)
    payload["products"][0]["color"] = "tampered"
    catalog.write_bytes(stable_json_bytes(payload))

    with pytest.raises(AuthorityContractError, match="differs|checksum|stale|changed"):
        build_car_t6_readiness(isolated_root)
    assert _outputs_absent(isolated_root)


def test_atomic_failure_removes_all_partial_outputs(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected CAR-T6 failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError, match="injected CAR-T6"):
        _run(isolated_root)
    assert _outputs_absent(isolated_root)


def test_cli_supports_readiness_authorized_creation_and_check(isolated_root: Path) -> None:
    readiness = subprocess.run(
        [sys.executable, str(CLI), "--root", str(isolated_root), "--readiness"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert readiness.returncode == 0, readiness.stderr
    assert json.loads(readiness.stdout)["approved_exact_variant_count"] == 20

    generic = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(isolated_root),
            "--owner-response",
            "繼續下一步",
            "--authorized-car-t6-owner-response",
            "繼續下一步",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert generic.returncode != 0
    assert "fresh explicit" in generic.stderr

    command = [
        sys.executable,
        str(CLI),
        "--root",
        str(isolated_root),
        "--owner-response",
        AUTHORIZED_RESPONSE,
        "--authorized-car-t6-owner-response",
        AUTHORIZED_RESPONSE,
        "--authorized-at",
        AUTHORIZED_AT.isoformat(),
    ]
    created = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == "created"
    checked = subprocess.run(
        [*command[:-2], "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.strip() == "unchanged"
