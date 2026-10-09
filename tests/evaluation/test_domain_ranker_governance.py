from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.domain_ranker_governance import (
    AUTHORIZATION_PATH,
    CATALOG_PATH,
    FROZEN_AUTHORIZATION_FILE_SHA256,
    FROZEN_GOVERNANCE_FILE_SHA256,
    GOVERNANCE_PATH,
    GOVERNANCE_V2_PATH,
    HUMAN_DATASET_PATH,
    NEGATIVE_HOLDOUT_PATH,
    NO_MATCH_GOVERNANCE_PATH,
    POSITIVE_DATASET_PATH,
    PUBLICATION_AMENDMENT_PATH,
    _contains_row_level_key,
    _validate_authorization,
    _validate_effective_governance,
    _validate_publication_amendment,
    audit_inputs,
    build_authorization,
    build_effective_governance,
    build_governance,
    build_publication_amendment,
    check,
    check_publication_amendment,
)
from product_variant_resolver.pointwise_no_match_governance import (
    AUTHORIZATION_PATH as NO_MATCH_AUTHORIZATION_PATH,
)
from product_variant_resolver.pointwise_no_match_readiness import (
    OUTPUT as NO_MATCH_READINESS_PATH,
)

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _isolated_root(tmp_path: Path) -> Path:
    paths = (
        POSITIVE_DATASET_PATH,
        HUMAN_DATASET_PATH,
        CATALOG_PATH,
        NEGATIVE_HOLDOUT_PATH,
        NO_MATCH_READINESS_PATH,
        NO_MATCH_AUTHORIZATION_PATH,
        NO_MATCH_GOVERNANCE_PATH,
        AUTHORIZATION_PATH,
        GOVERNANCE_PATH,
        PUBLICATION_AMENDMENT_PATH,
        GOVERNANCE_V2_PATH,
    )
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        target.chmod(0o644)
    return tmp_path


def test_materialized_gate_is_exact_and_local_only() -> None:
    authorization = build_authorization(ROOT)
    governance = check(ROOT, require_local_catalog=True)

    assert _load(ROOT / AUTHORIZATION_PATH) == authorization
    assert governance == build_governance(ROOT, authorization)
    assert governance["status"] == "active_for_owner_attested_local_only_development"
    assert governance["rights_state"] == "owner_attested_not_independently_verified"
    assert governance["admitted_aggregate_counts"] == {
        "positive_development": 100,
        "no_match_calibration_fit": 32,
        "no_match_threshold_selection": 20,
    }
    assert governance["permissions"]["positive_local_domain_fine_tuning"] is True
    assert governance["permissions"]["no_match_ranker_fine_tuning"] is False
    assert governance["permissions"]["public_checkpoint_or_weights"] is False
    assert governance["permissions"]["runtime_activation"] is False
    assert governance["next_allowed_action"] == "separate_owner_authorization_for_drsp_t2"
    assert "owner_statement" not in authorization
    assert len(authorization["owner_statement_sha256"]) == 64


def test_public_artifacts_contain_no_row_level_output() -> None:
    authorization = _load(ROOT / AUTHORIZATION_PATH)
    governance = _load(ROOT / GOVERNANCE_PATH)

    assert not _contains_row_level_key(authorization)
    assert not _contains_row_level_key(governance)
    serialized = json.dumps([authorization, governance], ensure_ascii=False).casefold()
    assert "http://" not in serialized
    assert "https://" not in serialized


def test_audit_recomputes_every_frozen_binding() -> None:
    audit = audit_inputs(ROOT)

    assert audit["positive"]["total_count"] == 153
    assert audit["positive"]["permanently_excluded_test_count"] == 53
    assert audit["no_match_development"]["calibration_fit_count"] == 32
    assert audit["no_match_development"]["threshold_selection_count"] == 20
    assert audit["catalog"]["record_count"] == 1763
    assert audit["catalog"]["local_file_revalidated"] is True
    assert audit["negative_holdout"]["permanently_excluded_count"] == 20


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (POSITIVE_DATASET_PATH, "positive dataset differs"),
        (HUMAN_DATASET_PATH, "human dataset differs"),
        (CATALOG_PATH, "frozen catalog differs"),
        (NEGATIVE_HOLDOUT_PATH, "opened negative holdout differs"),
    ],
)
def test_input_drift_fails_closed(tmp_path: Path, path: Path, message: str) -> None:
    isolated = _isolated_root(tmp_path)
    target = isolated / path
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(ValueError, match=message):
        audit_inputs(isolated)


def test_owner_authorization_scope_tamper_fails_closed() -> None:
    authorization = build_authorization(ROOT)
    authorization["publication_and_retention"]["checkpoint_or_weights_publication_allowed"] = True

    with pytest.raises(ValueError, match="stale, generic, or out of scope"):
        _validate_authorization(authorization, ROOT)


def test_public_check_can_validate_when_git_ignored_catalog_is_not_mounted(
    tmp_path: Path,
) -> None:
    isolated = _isolated_root(tmp_path)
    (isolated / CATALOG_PATH).unlink()

    governance = check(isolated, require_local_catalog=False)

    assert governance["bindings"]["catalog_sha256"]
    with pytest.raises(ValueError, match="required regular file"):
        check(isolated, require_local_catalog=True)


def test_frozen_t1_artifacts_are_byte_identical_after_publication_amendment() -> None:
    assert hashlib.sha256((ROOT / AUTHORIZATION_PATH).read_bytes()).hexdigest() == (
        FROZEN_AUTHORIZATION_FILE_SHA256
    )
    assert hashlib.sha256((ROOT / GOVERNANCE_PATH).read_bytes()).hexdigest() == (
        FROZEN_GOVERNANCE_FILE_SHA256
    )


def test_publication_amendment_separates_permission_release_and_execution() -> None:
    amendment = build_publication_amendment(ROOT)
    effective = check_publication_amendment(ROOT, require_local_catalog=True)

    assert _load(ROOT / PUBLICATION_AMENDMENT_PATH) == amendment
    assert effective == build_effective_governance(ROOT, amendment)
    publication = effective["publication_state"]
    assert publication["hard_negative_pair_package"] == {
        "owner_authorized": True,
        "published": False,
        "release_gate_passed": False,
        "row_level_package": True,
    }
    assert publication["fine_tuned_checkpoint"] == {
        "format": "safetensors",
        "owner_authorized": True,
        "published": False,
        "release_gate_passed": False,
    }
    assert publication["fresh_final_aggregate_report"] == {
        "evaluation_authorized": False,
        "executed": False,
        "publication_allowed": True,
        "published": False,
    }
    assert publication["runtime_code_config_and_model_manifest"] == {
        "activated": False,
        "activation_authorized": False,
        "publication_allowed": True,
        "published": False,
    }
    assert (
        publication["fresh_final_row_level_queries_or_predictions"]["publication_allowed"] is False
    )
    assert publication["public_endpoint"]["authorized"] is False
    assert effective["rights_state"] == "owner_attested_not_independently_verified"


def test_publication_artifacts_contain_only_digest_not_owner_message() -> None:
    amendment = _load(ROOT / PUBLICATION_AMENDMENT_PATH)
    effective = _load(ROOT / GOVERNANCE_V2_PATH)

    assert "owner_statement" not in amendment
    assert len(amendment["owner_statement_sha256"]) == 64
    assert not _contains_row_level_key(amendment)
    assert not _contains_row_level_key(effective)
    serialized = json.dumps([amendment, effective], ensure_ascii=False)
    assert "/Users/" not in serialized
    assert "http://" not in serialized
    assert "https://" not in serialized


def test_publication_release_gates_preserve_denylist_and_safe_transport() -> None:
    effective = _load(ROOT / GOVERNANCE_V2_PATH)
    release_gates = effective["release_gate_requirements"]

    assert effective["permanent_denylist"]["positive_test"]["count"] == 53
    assert effective["permanent_denylist"]["negative_holdout"]["count"] == 20
    assert "permanent_denylist_intersection_is_zero" in release_gates["common"]
    assert "secret_pii_and_local_path_scan_passed" in release_gates["common"]
    assert "artifact_license_and_notice_present" in release_gates["common"]
    assert "safetensors_only_no_pickle_payload" in release_gates["fine_tuned_checkpoint"]
    assert release_gates["ordinary_git_large_blob_commit_allowed"] is False
    assert "git_lfs_or_release_asset" in release_gates["large_checkpoint_transport"]


def test_publication_amendment_tamper_fails_closed(tmp_path: Path) -> None:
    isolated = _isolated_root(tmp_path)
    amendment = _load(isolated / PUBLICATION_AMENDMENT_PATH)
    amendment["publication_permissions"]["fine_tuned_checkpoint"]["published"] = True

    with pytest.raises(ValueError, match="stale, tampered, or out of scope"):
        _validate_publication_amendment(amendment, isolated)


def test_effective_governance_tamper_fails_closed(tmp_path: Path) -> None:
    isolated = _isolated_root(tmp_path)
    amendment = _load(isolated / PUBLICATION_AMENDMENT_PATH)
    effective = _load(isolated / GOVERNANCE_V2_PATH)
    effective["permissions"]["runtime_activation"] = True

    with pytest.raises(ValueError, match="stale, tampered, or out of scope"):
        _validate_effective_governance(effective, isolated, amendment)


def test_frozen_t1_byte_drift_blocks_publication_check(tmp_path: Path) -> None:
    isolated = _isolated_root(tmp_path)
    target = isolated / GOVERNANCE_PATH
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="frozen DRSP-T1 governance differs"):
        check_publication_amendment(isolated, require_local_catalog=True)


def test_publication_check_works_without_git_ignored_catalog(tmp_path: Path) -> None:
    isolated = _isolated_root(tmp_path)
    (isolated / CATALOG_PATH).unlink()

    effective = check_publication_amendment(isolated, require_local_catalog=False)

    assert effective["bindings"]["catalog_sha256"]
    with pytest.raises(ValueError, match="required regular file"):
        check_publication_amendment(isolated, require_local_catalog=True)


def test_gitignore_allows_only_named_publication_packages() -> None:
    data_root = "data/evaluation/domain-ranker-selective-prediction-development-v1"
    ignored_paths = (
        f"{data_root}/local-scratch/pairs.jsonl",
        f"{data_root}/unreviewed-pairs/pairs.jsonl",
        f"{data_root}/raw-training-projections.jsonl",
        f"{data_root}/split-membership.json",
        f"{data_root}/calibration-rows.jsonl",
        f"{data_root}/fresh-final-row-predictions.jsonl",
        "artifacts/domain-ranker-selective-prediction-development-v1/local-run/optimizer.pt",
        "artifacts/domain-ranker-selective-prediction-development-v1/cache/model.tmp",
    )
    public_paths = (
        f"{data_root}/owner-authorization.json",
        f"{data_root}/governance.json",
        f"{data_root}/publication-amendment.json",
        f"{data_root}/governance-v2.json",
        f"{data_root}/public-hard-negative-pairs-v1/pairs.jsonl",
        (
            "artifacts/domain-ranker-selective-prediction-development-v1/"
            "public-checkpoint-v1/model.safetensors"
        ),
    )

    for path in ignored_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, path
    for path in public_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 1, path
