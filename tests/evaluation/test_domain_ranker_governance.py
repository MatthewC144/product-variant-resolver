from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.domain_ranker_governance import (
    AUTHORIZATION_PATH,
    CATALOG_PATH,
    GOVERNANCE_PATH,
    HUMAN_DATASET_PATH,
    NEGATIVE_HOLDOUT_PATH,
    NO_MATCH_GOVERNANCE_PATH,
    POSITIVE_DATASET_PATH,
    _contains_row_level_key,
    _validate_authorization,
    audit_inputs,
    build_authorization,
    build_governance,
    check,
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
