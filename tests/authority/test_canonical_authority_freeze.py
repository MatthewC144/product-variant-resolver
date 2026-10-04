from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

import product_variant_resolver.canonical_authority_freeze as freeze
from product_variant_resolver.canonical_authority_freeze import (
    AUTHORITY_BUNDLE_REFERENCE,
    AUTHORITY_MANIFEST_REFERENCE,
    FREEZE_AUTHORIZATION_REFERENCE,
    CarT5FFreezeAuthorization,
    build_car_t5f_readiness,
    freeze_authority_bundle,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityBundle,
    AuthorityBundleManifest,
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "freeze_canonical_authority_bundle.py"
AUTHORIZED_RESPONSE = (
    "我批准執行 CAR-T5F 並封存目前的 authority bundle；若條件不符則發布 exact shortfalls。"
    "不授權 CAR-T6，也不授權 RHB-T5。"
)
AUTHORIZED_AT = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


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
        FREEZE_AUTHORIZATION_REFERENCE,
        AUTHORITY_BUNDLE_REFERENCE,
        AUTHORITY_MANIFEST_REFERENCE,
    ):
        (root / reference).unlink(missing_ok=True)
    return root


def _read(root: Path, reference: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((root / reference).read_text(encoding="utf-8")))


def _freeze(root: Path, *, check: bool = False) -> str:
    return freeze_authority_bundle(
        root,
        owner_response_verbatim=AUTHORIZED_RESPONSE,
        authorized_car_t5f_owner_response=AUTHORIZED_RESPONSE,
        authorized_at=None if check else AUTHORIZED_AT,
        check=check,
    )


def test_readiness_revalidates_complete_two_gate_state_without_writing(
    isolated_root: Path,
) -> None:
    before = {
        reference: (isolated_root / reference).exists()
        for reference in (
            FREEZE_AUTHORIZATION_REFERENCE,
            AUTHORITY_BUNDLE_REFERENCE,
            AUTHORITY_MANIFEST_REFERENCE,
        )
    }
    report = build_car_t5f_readiness(isolated_root)
    after = {
        reference: (isolated_root / reference).exists()
        for reference in (
            FREEZE_AUTHORIZATION_REFERENCE,
            AUTHORITY_BUNDLE_REFERENCE,
            AUTHORITY_MANIFEST_REFERENCE,
        )
    }

    assert before == after == {reference: False for reference in before}
    assert report.approved_exact_count == 20
    assert report.reviewed_count == report.staged_count == 0
    assert report.family_count == report.qualifying_family_count == 7
    assert [item.approved_variant_count for item in report.family_composition] == [
        3,
        3,
        3,
        2,
        3,
        3,
        3,
    ]
    assert report.proposed_gate_status == "eligible_for_rhb_t4_reaudit"
    assert not report.car_t6_authorized and not report.rhb_t5_authorized


def test_generic_continuation_and_ambiguous_gate_text_fail_without_outputs(
    isolated_root: Path,
) -> None:
    with pytest.raises(AuthorityContractError, match="fresh explicit"):
        freeze_authority_bundle(
            isolated_root,
            owner_response_verbatim="繼續下一步",
            authorized_car_t5f_owner_response="繼續下一步",
            authorized_at=AUTHORIZED_AT,
        )

    assert not (isolated_root / FREEZE_AUTHORIZATION_REFERENCE).exists()
    assert not (isolated_root / AUTHORITY_BUNDLE_REFERENCE).exists()
    assert not (isolated_root / AUTHORITY_MANIFEST_REFERENCE).exists()


def test_mismatched_owner_response_fails_closed(isolated_root: Path) -> None:
    with pytest.raises(AuthorityContractError, match="differs"):
        freeze_authority_bundle(
            isolated_root,
            owner_response_verbatim=AUTHORIZED_RESPONSE,
            authorized_car_t5f_owner_response=f"{AUTHORIZED_RESPONSE} changed",
            authorized_at=AUTHORIZED_AT,
        )


def test_freezes_bundle_privately_authorized_and_replays_unchanged(isolated_root: Path) -> None:
    assert _freeze(isolated_root) == "created"
    first = {
        reference: (isolated_root / reference).read_bytes()
        for reference in (
            FREEZE_AUTHORIZATION_REFERENCE,
            AUTHORITY_BUNDLE_REFERENCE,
            AUTHORITY_MANIFEST_REFERENCE,
        )
    }
    assert _freeze(isolated_root) == "unchanged"
    assert _freeze(isolated_root, check=True) == "unchanged"
    assert {reference: (isolated_root / reference).read_bytes() for reference in first} == first

    authorization = CarT5FFreezeAuthorization.model_validate(
        _read(isolated_root, FREEZE_AUTHORIZATION_REFERENCE)
    )
    bundle = AuthorityBundle.model_validate(_read(isolated_root, AUTHORITY_BUNDLE_REFERENCE))
    manifest = AuthorityBundleManifest.model_validate(
        _read(isolated_root, AUTHORITY_MANIFEST_REFERENCE)
    )
    assert authorization.gate == "CAR-T5F"
    assert len(bundle.records) == 20
    assert all(record.status.value == "approved_exact" for record in bundle.records)
    assert manifest.authority_bundle_sha256 == content_sha256(bundle.model_dump(mode="json"))
    assert manifest.approved_distinct_variant_count == 20
    assert manifest.qualifying_family_count == 7
    assert manifest.gate_status == "eligible_for_rhb_t4_reaudit"
    assert manifest.shortfalls.exact_variant_shortfall == 0
    assert manifest.shortfalls.qualifying_family_shortfall == 0
    assert not manifest.rhb_t5_authorized

    public = first[AUTHORITY_BUNDLE_REFERENCE] + first[AUTHORITY_MANIFEST_REFERENCE]
    assert AUTHORIZED_RESPONSE.encode() not in public
    assert stat_mode(isolated_root / FREEZE_AUTHORIZATION_REFERENCE) == 0o600
    assert stat_mode(isolated_root / AUTHORITY_BUNDLE_REFERENCE) == 0o644
    assert stat_mode(isolated_root / AUTHORITY_MANIFEST_REFERENCE) == 0o644
    with pytest.raises(AuthorityContractError, match="already materialized"):
        build_car_t5f_readiness(isolated_root)


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_stale_candidate_checksum_blocks_readiness(isolated_root: Path) -> None:
    path = isolated_root / freeze.AUTHORITY_CANDIDATES_REFERENCE
    payload = _read(isolated_root, freeze.AUTHORITY_CANDIDATES_REFERENCE)
    payload["status_counts"]["approved_exact"] = 19
    path.write_bytes(stable_json_bytes(payload))

    with pytest.raises(ValueError, match="counts are stale|checksum is stale"):
        build_car_t5f_readiness(isolated_root)
    assert not (isolated_root / AUTHORITY_BUNDLE_REFERENCE).exists()


def test_atomic_failure_removes_all_partial_outputs(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected CAR-T5F failure")
        real_replace(source, target)

    monkeypatch.setattr(freeze.os, "replace", fail_second)
    with pytest.raises(OSError, match="injected CAR-T5F"):
        _freeze(isolated_root)
    for reference in (
        FREEZE_AUTHORIZATION_REFERENCE,
        AUTHORITY_BUNDLE_REFERENCE,
        AUTHORITY_MANIFEST_REFERENCE,
    ):
        assert not (isolated_root / reference).exists()


def test_cli_readiness_and_owner_authorized_freeze(isolated_root: Path) -> None:
    readiness = subprocess.run(
        [sys.executable, str(CLI), "--root", str(isolated_root), "--readiness"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert readiness.returncode == 0, readiness.stderr
    assert json.loads(readiness.stdout)["approved_exact_count"] == 20

    generic = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(isolated_root),
            "--owner-response",
            "繼續下一步",
            "--authorized-car-t5f-owner-response",
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
        "--authorized-car-t5f-owner-response",
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
