from __future__ import annotations

import json
import os
import shutil
import stat
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from product_variant_resolver.representative_benchmark import ChallengeTag
from product_variant_resolver.representative_benchmark_query_authoring import (
    AUTHORING_INPUT_REFERENCE,
    OWNER_AUTHORIZATION_REFERENCE,
    OWNER_AUTHORIZATION_TEXT_SHA256,
    PROJECTION_REFERENCE,
    QUERY_PACK_MANIFEST_REFERENCE,
    QUERY_PACK_REFERENCE,
    QueryAuthoringError,
    RhbT5OwnerAuthorization,
    build_query_pack,
    materialize_query_pack,
    validate_materialized_query_pack,
)

ROOT = Path(__file__).resolve().parents[2]
RHB = Path("data/evaluation/representative-hard-benchmark-v1")
SAFE_PUBLIC_INPUTS = (
    Path(".gitignore"),
    RHB / "source-inventory.json",
    RHB / "source-inventory-manifest.json",
    RHB / "source-decisions.json",
    RHB / "query-authoring-source-manifest.json",
    Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json"),
)
SAFE_PRIVATE_INPUTS = (
    PROJECTION_REFERENCE,
    OWNER_AUTHORIZATION_REFERENCE,
    AUTHORING_INPUT_REFERENCE,
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
    for reference in (*SAFE_PUBLIC_INPUTS, *SAFE_PRIVATE_INPUTS):
        _copy(root, reference)
    os.chmod(root / PROJECTION_REFERENCE.parent, 0o700)
    return root


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_real_pack_is_exactly_60_unique_non_synthetic_output_blind_cases() -> None:
    pack, manifest = validate_materialized_query_pack(ROOT)

    assert len(pack.cases) == manifest.record_count == 60
    assert len({case.query.casefold() for case in pack.cases}) == 60
    assert len({case.source_record_ref for case in pack.cases}) == 60
    assert len({case.evidence_event_group_key for case in pack.cases}) == 60
    assert all(case.source_id == "human-labeled-real-noisy-v1" for case in pack.cases)
    assert all(case.authored_by == "fresh_output_blind_independent_agent" for case in pack.cases)
    assert all(not case.public_safe and not case.resolver_output_viewed for case in pack.cases)
    assert not pack.representative_pilot
    assert pack.publication_scope == "local_only"

    payload = pack.model_dump(mode="json")
    forbidden = ("expected", "canonical_uuid", "correct", "rank", "failure", "split")
    for case in payload["cases"]:
        keys = set(case)
        assert "resolver_output_viewed" in keys
        assert all(not any(token in key for token in forbidden) for key in keys)


def test_public_manifest_is_aggregate_only_and_leaks_no_private_rows() -> None:
    pack, manifest = validate_materialized_query_pack(ROOT)
    public_payload = manifest.model_dump(mode="json", by_alias=True)
    assert set(public_payload) == {
        "schema",
        "sha256",
        "record_count",
        "non_sensitive_aggregate",
        "non_sensitive_summary",
    }
    assert "authoring_role" not in public_payload
    assert "reviewer_role" not in public_payload
    public_text = json.dumps(public_payload, ensure_ascii=False)
    assert "project_owner" not in public_text
    authorization = _read(ROOT / OWNER_AUTHORIZATION_REFERENCE)
    assert authorization["authorization_text"] not in public_text
    for case in pack.cases:
        assert case.query not in public_text
        assert case.source_record_ref is not None
        assert case.source_record_ref not in public_text
        assert case.case_id not in public_text
        assert case.family_group_key not in public_text
        assert case.evidence_event_group_key not in public_text
    aggregate = manifest.non_sensitive_aggregate
    assert not aggregate.contains_query_text
    assert not aggregate.contains_source_record_refs
    assert not aggregate.contains_expected_status_or_uuid
    assert not aggregate.contains_resolver_output_or_rank
    assert not aggregate.contains_human_labels
    assert not aggregate.contains_failure_categories
    assert not aggregate.contains_split
    assert not aggregate.rhb_t6_authorized
    assert not aggregate.rhb_t7_authorized
    assert not aggregate.resolver_evaluation_authorized
    assert aggregate.owner_authorization_sha256 == authorization["authorization_sha256"]


def test_challenge_coverage_is_complete_where_supported_and_shortfalls_are_honest() -> None:
    _pack, manifest = build_query_pack(ROOT)
    aggregate = manifest.non_sensitive_aggregate
    assert set(aggregate.provisional_challenge_tag_counts) == {tag.value for tag in ChallengeTag}
    assert aggregate.provisional_challenge_tag_counts == {
        "same_casting_different_release": 9,
        "alias_or_abbreviation": 43,
        "missing_metadata": 35,
        "conflicting_year": 1,
        "conflicting_color": 1,
        "conflicting_series": 0,
        "conflicting_identifier": 2,
        "distractor_quantity_or_lot": 32,
        "unknown_to_catalog": 0,
    }
    assert aggregate.provisional_challenge_tag_shortfalls == {
        "same_casting_different_release": 0,
        "alias_or_abbreviation": 0,
        "missing_metadata": 0,
        "conflicting_year": 3,
        "conflicting_color": 3,
        "conflicting_series": 4,
        "conflicting_identifier": 2,
        "distractor_quantity_or_lot": 0,
        "unknown_to_catalog": 4,
    }
    assert not aggregate.provisional_surface_coverage_complete
    assert not aggregate.challenge_coverage_verified
    assert aggregate.authoring_status == (
        "authoring_artifact_pending_owner_labels_with_declared_surface_shortfalls"
    )


def test_owner_authorization_rejects_generic_or_mismatched_scope() -> None:
    payload = _read(ROOT / OWNER_AUTHORIZATION_REFERENCE)
    assert payload["authorization_text_sha256"] == OWNER_AUTHORIZATION_TEXT_SHA256
    payload["authorization_text"] = "I approve RHB-T5."
    with pytest.raises(ValidationError, match="generic or mismatched"):
        RhbT5OwnerAuthorization.model_validate(payload)

    payload = _read(ROOT / OWNER_AUTHORIZATION_REFERENCE)
    payload["rhb_t6_authorized"] = True
    with pytest.raises(ValidationError):
        RhbT5OwnerAuthorization.model_validate(payload)

    payload = _read(ROOT / OWNER_AUTHORIZATION_REFERENCE)
    payload["authorization_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="self-binding checksum"):
        RhbT5OwnerAuthorization.model_validate(payload)


def test_authoring_input_binds_authorization_and_cannot_predate_it(
    isolated_root: Path,
) -> None:
    input_path = isolated_root / AUTHORING_INPUT_REFERENCE
    payload = _read(input_path)
    payload["owner_authorization_sha256"] = "0" * 64
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(input_path, 0o600)
    with pytest.raises(QueryAuthoringError, match="different owner authorization"):
        build_query_pack(isolated_root)

    _copy(isolated_root, AUTHORING_INPUT_REFERENCE)
    payload = _read(input_path)
    payload["authored_at"] = "2026-10-03T23:59:59Z"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(input_path, 0o600)
    with pytest.raises(QueryAuthoringError, match="cannot predate"):
        build_query_pack(isolated_root)

    _copy(isolated_root, AUTHORING_INPUT_REFERENCE)
    payload = _read(input_path)
    payload["authored_by"] = "project_owner"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(input_path, 0o600)
    with pytest.raises(ValidationError):
        build_query_pack(isolated_root)


def test_same_casting_surface_tag_rejects_singleton_family(isolated_root: Path) -> None:
    input_path = isolated_root / AUTHORING_INPUT_REFERENCE
    payload = _read(input_path)
    selections = cast(list[dict[str, Any]], payload["selections"])
    family_counts = Counter(selection["family_group_key"] for selection in selections)
    singleton = next(
        selection
        for selection in selections
        if family_counts[selection["family_group_key"]] == 1
        and "same_casting_different_release" not in selection["challenge_tags"]
    )
    singleton["challenge_tags"].insert(0, "same_casting_different_release")
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(input_path, 0o600)

    with pytest.raises(ValidationError, match="at least two selected family rows"):
        build_query_pack(isolated_root)


def test_tracked_authoring_files_exclude_private_owner_text_and_source_path() -> None:
    authorization = _read(ROOT / OWNER_AUTHORIZATION_REFERENCE)
    private_owner_text = cast(str, authorization["authorization_text"])
    private_source_path = "_".join(("human", "labeled", "names")) + ".json"  # noqa: FLY002
    tracked_references = (
        Path("src/product_variant_resolver/representative_benchmark_query_authoring.py"),
        Path("scripts/build_representative_hard_benchmark_query_pack.py"),
        Path("tests/evaluation/test_representative_benchmark_query_authoring.py"),
        QUERY_PACK_MANIFEST_REFERENCE,
    )
    for reference in tracked_references:
        tracked_text = (ROOT / reference).read_text(encoding="utf-8")
        assert private_owner_text not in tracked_text
        assert private_source_path not in tracked_text


def test_projection_and_t3_hash_tampering_fail_closed(isolated_root: Path) -> None:
    projection_path = isolated_root / PROJECTION_REFERENCE
    projection = _read(projection_path)
    projection["records"][0]["query"] = "tampered"
    projection_path.write_text(json.dumps(projection), encoding="utf-8")
    os.chmod(projection_path, 0o600)
    with pytest.raises(QueryAuthoringError, match="projection checksum"):
        build_query_pack(isolated_root)

    _copy(isolated_root, PROJECTION_REFERENCE)
    decisions_path = isolated_root / RHB / "source-decisions.json"
    decisions_path.write_bytes(decisions_path.read_bytes() + b"\n")
    with pytest.raises(QueryAuthoringError, match="different T3 decisions"):
        build_query_pack(isolated_root)


def test_materialization_is_private_atomic_and_check_replays(isolated_root: Path) -> None:
    assert materialize_query_pack(isolated_root) == "created"
    pack_path = isolated_root / QUERY_PACK_REFERENCE
    manifest_path = isolated_root / QUERY_PACK_MANIFEST_REFERENCE
    assert stat.S_IMODE(pack_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(pack_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(manifest_path.stat().st_mode) == 0o644
    assert materialize_query_pack(isolated_root) == "unchanged"
    assert materialize_query_pack(isolated_root, check=True) == "unchanged"


def test_second_replace_failure_rolls_back_both_outputs(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected authoring failure")
        real_replace(source, target)

    monkeypatch.setattr(
        "product_variant_resolver.representative_benchmark_query_authoring.os.replace",
        fail_second,
    )
    with pytest.raises(OSError, match="injected authoring"):
        materialize_query_pack(isolated_root)
    assert not (isolated_root / QUERY_PACK_REFERENCE).exists()
    assert not (isolated_root / QUERY_PACK_MANIFEST_REFERENCE).exists()


def test_private_pack_tamper_and_partial_outputs_fail_closed(isolated_root: Path) -> None:
    assert materialize_query_pack(isolated_root) == "created"
    pack_path = isolated_root / QUERY_PACK_REFERENCE
    payload = _read(pack_path)
    payload["cases"][0]["query"] = "tampered"
    pack_path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(pack_path, 0o600)
    with pytest.raises(QueryAuthoringError, match="stale or tampered"):
        validate_materialized_query_pack(isolated_root)

    pack_path.unlink()
    with pytest.raises(QueryAuthoringError, match="partial"):
        materialize_query_pack(isolated_root)


def test_fresh_clone_shape_cannot_recreate_private_rows(tmp_path: Path) -> None:
    root = tmp_path / "fresh-clone"
    root.mkdir()
    for reference in (*SAFE_PUBLIC_INPUTS, QUERY_PACK_MANIFEST_REFERENCE):
        _copy(root, reference)

    with pytest.raises(QueryAuthoringError, match="private authoring directory"):
        materialize_query_pack(root, check=True)
    public_text = (root / QUERY_PACK_MANIFEST_REFERENCE).read_text(encoding="utf-8")
    pack, _manifest = validate_materialized_query_pack(ROOT)
    assert all(case.query not in public_text for case in pack.cases)


def test_authoring_module_has_no_resolver_network_label_split_or_raw_source_dependency() -> None:
    source = (
        ROOT / "src/product_variant_resolver/representative_benchmark_query_authoring.py"
    ).read_text(encoding="utf-8")
    private_source_path = "_".join(("human", "labeled", "names")) + ".json"  # noqa: FLY002
    forbidden = (
        f'Path("data/{private_source_path}")',
        "HUMAN_SOURCE_REFERENCE",
        "import requests",
        "import selenium",
        "import fastapi",
        "ResolverService",
        "labels.json",
        "held-labels.json",
        "split.json",
        ".resolve(",
    )
    assert all(token not in source for token in forbidden)
