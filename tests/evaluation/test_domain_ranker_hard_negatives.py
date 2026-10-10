from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar, cast

import pytest

import product_variant_resolver.domain_ranker_hard_negatives as hard_negative_module
from product_variant_resolver.domain_ranker_hard_negatives import (
    AUTHORIZATION_OUTPUT_PATH,
    DATA_CARD_PATH,
    MANIFEST_PATH,
    MAX_NEGATIVES_PER_QUERY,
    MIN_NEGATIVES_PER_QUERY,
    NOTICE_PATH,
    PACKAGE_DIRECTORY,
    PAIR_PATH,
    _candidate_category,
    _content_sha256,
    _pair_bytes,
    _sanitize_query,
    _scan_release_files,
    _validate_digest,
    _validate_pair_projection,
    build_package,
    check,
)
from product_variant_resolver.domain_ranker_partitions import (
    LOCAL_PARTITIONS_PATH,
    LOCAL_POOLS_PATH,
)

ROOT = Path(__file__).resolve().parents[2]
FixtureValue = TypeVar("FixtureValue")
DecoratorParameters = ParamSpec("DecoratorParameters")
DecoratorResult = TypeVar("DecoratorResult")


class FixtureDecorator(Protocol):
    def __call__(self, function: Callable[[], FixtureValue]) -> Callable[[], FixtureValue]: ...


module_fixture = cast(FixtureDecorator, pytest.fixture(scope="module"))


class ParametrizeDecorator(Protocol):
    def __call__(
        self, function: Callable[DecoratorParameters, DecoratorResult]
    ) -> Callable[DecoratorParameters, DecoratorResult]: ...


@module_fixture
def built() -> tuple[
    dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]
]:
    return build_package(ROOT)


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        assert isinstance(payload, dict)
        result.append(payload)
    return result


def test_t3_is_train_only_and_does_not_execute_downstream_work(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _authorization, rows, _data_card, _notice, manifest = built
    counts = manifest["aggregate_counts"]
    guardrails = manifest["guardrails"]

    assert counts["train_query_count"] == 70
    assert counts["selection_query_count_untouched"] == 30
    assert len({row["query_id"] for row in rows}) == 69
    assert counts["queries_with_at_least_one_defensible_negative"] == 69
    assert counts["queries_with_zero_defensible_negatives"] == 1
    assert guardrails == {
        "ranker_selection_queries_mined": 0,
        "ranker_selection_queries_scored": 0,
        "positive_test_queries_mined": 0,
        "positive_test_queries_scored": 0,
        "negative_holdout_queries_mined": 0,
        "negative_holdout_queries_scored": 0,
        "no_match_development_queries_mined": 0,
        "no_match_development_queries_scored": 0,
        "target_injections": 0,
        "candidate_pool_mutations": 0,
        "model_training_runs": 0,
        "model_selection_runs": 0,
        "calibration_fits": 0,
        "fresh_final_evaluations": 0,
        "runtime_default_changed": False,
    }


def test_maximum_and_majority_minimum_gates_are_enforced(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _authorization, rows, _data_card, _notice, manifest = built
    counts_by_query: dict[str, int] = {}
    for row in rows:
        query_id = str(row["query_id"])
        counts_by_query[query_id] = counts_by_query.get(query_id, 0) + 1

    assert max(counts_by_query.values()) <= MAX_NEGATIVES_PER_QUERY
    assert sum(count >= MIN_NEGATIVES_PER_QUERY for count in counts_by_query.values()) == 69
    assert manifest["aggregate_counts"]["queries_with_at_least_two_defensible_negatives"] == 69
    assert 69 >= manifest["aggregate_counts"]["strict_majority_gate_minimum"]


def test_category_priority_and_tie_break_are_deterministic(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _authorization, rows, _data_card, _notice, manifest = built
    first = [row["negative_category"] for row in rows if row["query_id"] == "pvr-query-001"]
    priority = manifest["mining_contract"]["category_priority"]

    assert first == sorted(first, key=priority.index)
    assert set(manifest["negative_category_counts"]) <= set(priority)
    assert manifest["negative_category_counts"]["same_casting_wrong_exact_release"] > 0
    assert manifest["negative_category_counts"]["high_generic_minilm_score"] > 0
    assert manifest["negative_category_counts"]["high_rrf_rank"] > 0


def test_ambiguous_same_family_sibling_is_held() -> None:
    target = {
        "brand": "Hot Wheels",
        "casting": "Example Car",
        "release_year": 2024,
        "series": "Series A",
        "toy_number": "AAA01",
        "collector_number": "001",
        "series_position": "1/5",
        "color": None,
    }
    sibling = {
        "brand": "Hot Wheels",
        "casting_name": "Example Car",
        "release_year": 2024,
        "series": "Series A",
        "toy_number": "AAA02",
        "collector_number": "001",
        "series_position": "1/5",
        "color": None,
    }

    category, held = _candidate_category(
        "hot wheels example car", target, sibling, generic_rank=1, rrf_rank=1
    )

    assert category is None
    assert held == "same_family_without_query_supported_release_discriminator"


def test_same_family_with_explicit_identifier_is_defensible() -> None:
    target = {
        "brand": "Hot Wheels",
        "casting": "Example Car",
        "release_year": 2024,
        "series": "Series A",
        "toy_number": "AAA01",
        "collector_number": "001",
        "series_position": "1/5",
        "color": None,
    }
    sibling = {
        "brand": "Hot Wheels",
        "casting_name": "Example Car",
        "release_year": 2024,
        "series": "Series A",
        "toy_number": "AAA02",
        "collector_number": "001",
        "series_position": "1/5",
        "color": None,
    }

    category, held = _candidate_category(
        "hot wheels example car aaa01", target, sibling, generic_rank=1, rrf_rank=1
    )

    assert category == "same_casting_wrong_exact_release"
    assert held is None


def test_public_projection_is_minimal_and_has_no_private_identifiers(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _authorization, rows, _data_card, _notice, _manifest = built
    _validate_pair_projection(rows)
    serialized = _pair_bytes(rows).decode()

    assert "isr-" not in serialized
    assert "selenium-row-" not in serialized
    assert "canonical_uuid" not in serialized
    assert "source_url" not in serialized
    assert "image_url" not in serialized
    assert "generic_pointwise_score" not in serialized
    assert all(str(row["query_id"]).startswith("pvr-query-") for row in rows)
    assert all(str(row["pair_id"]).startswith("pvr-pair-") for row in rows)


def test_query_projection_removes_contact_and_known_seller_platform_tokens() -> None:
    projected = _sanitize_query(
        "Hot Wheels Car at @seller seller@example.com https://shop.test Amazon Etsy Poshmark"
    )

    assert "seller" not in projected
    assert "example" not in projected
    assert "http" not in projected
    assert "amazon" not in projected
    assert "etsy" not in projected
    assert "poshmark" not in projected


def test_release_scan_rejects_secret_pii_path_and_executable_payload() -> None:
    unsafe = _scan_release_files(
        {
            "pairs.jsonl": b'{"query_text":"contact me at a@example.com"}\n',
            "bad.sh": b"#!/bin/sh\necho /Users/example/.env\n",
        }
    )

    assert unsafe["passed"] is False
    assert unsafe["finding_counts"]["email"] == 1
    assert unsafe["finding_counts"]["local_path"] == 1
    assert unsafe["finding_counts"]["executable_or_unapproved_format"] == 1
    assert unsafe["finding_counts"]["executable_or_binary_payload"] == 1


expanded_release_scan_cases = cast(
    ParametrizeDecorator,
    pytest.mark.parametrize(
        ("name", "payload", "finding"),
        [
            ("aws.json", b'{"value":"AKIAIOSFODNN7EXAMPLE"}\n', "aws_access_key"),
            (
                "auth.json",
                b'{"header":"Authorization: Bearer abcdefghijklmnop"}\n',
                "authorization_credential",
            ),
            (
                "env.json",
                b'{"path":"../private/.env.production"}\n',
                "secret_file_or_traversal_path",
            ),
            (
                "phone.json",
                b'{"contact":"+1 202 555 0123"}\n',
                "formatted_phone_contact",
            ),
        ],
    ),
)


@expanded_release_scan_cases
def test_release_scan_catches_expanded_secret_and_contact_shapes(
    name: str, payload: bytes, finding: str
) -> None:
    result = _scan_release_files({name: payload})

    assert result["passed"] is False
    assert result["finding_counts"][finding] >= 1


def test_release_scan_does_not_treat_pure_product_barcode_as_phone() -> None:
    result = _scan_release_files({"pairs.jsonl": b'{"barcode":"74299057854"}\n'})

    assert result["passed"] is True
    assert result["finding_counts"]["formatted_phone_contact"] == 0


def test_release_gate_and_denylist_audit_pass(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _authorization, _rows, _data_card, _notice, manifest = built
    gate = manifest["release_gate"]

    assert manifest["published"] is True
    assert manifest["release_gate_passed"] is True
    assert gate["permanent_denylist_query_or_identity_intersection"] == 0
    assert gate["secret_pii_contact_and_local_path_scan"]["passed"] is True
    assert gate["strict_field_minimization_passed"] is True
    assert gate["license_notice_present"] is True
    assert gate["final_manifest_secondary_scan_passed"] is True
    final_scan = _scan_release_files({"manifest.json": hard_negative_module._canonical_bytes(manifest)})
    assert final_scan["passed"] is True


def test_sanitized_public_query_projection_denylist_collision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = hard_negative_module._denylist
    partitions = json.loads((ROOT / LOCAL_PARTITIONS_PATH).read_text(encoding="utf-8"))
    train = next(
        row for row in partitions["members"] if row["partition"] == "ranker_train"
    )
    collision = _sanitize_query(train["query"])

    def colliding_denylist(
        root: Path, catalog_by_toy: dict[str, dict[str, Any]]
    ) -> dict[str, set[Any]]:
        result = original(root, catalog_by_toy)
        result["public_query_projections"].add(collision)
        return result

    monkeypatch.setattr(hard_negative_module, "_denylist", colliding_denylist)
    with pytest.raises(ValueError, match="permanent holdout denylist"):
        build_package(ROOT)


def test_exact_byte_regeneration_and_pool_immutability(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    before = hashlib.sha256((ROOT / LOCAL_POOLS_PATH).read_bytes()).hexdigest()
    repeated = build_package(ROOT)
    after = hashlib.sha256((ROOT / LOCAL_POOLS_PATH).read_bytes()).hexdigest()

    assert _pair_bytes(repeated[1]) == _pair_bytes(built[1])
    assert repeated[2:] == built[2:]
    assert before == after


def test_manifest_tamper_fails_closed(
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    tampered = copy.deepcopy(built[4])
    tampered["published"] = False

    with pytest.raises(ValueError, match="checksum is stale"):
        _validate_digest(tampered, "manifest_sha256", "DRSP-T3 manifest")


def test_package_file_tamper_fails_strict_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    authorization, rows, data_card, notice, manifest = built
    payloads = {
        AUTHORIZATION_OUTPUT_PATH: hard_negative_module._canonical_bytes(authorization),
        PAIR_PATH: _pair_bytes(rows),
        DATA_CARD_PATH: data_card,
        NOTICE_PATH: notice,
        MANIFEST_PATH: hard_negative_module._canonical_bytes(manifest),
    }
    for relative, payload in payloads.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o644)
    (tmp_path / PAIR_PATH).write_bytes((tmp_path / PAIR_PATH).read_bytes() + b"{}\n")
    monkeypatch.setattr(hard_negative_module, "build_package", lambda _root: built)

    with pytest.raises(ValueError, match="deterministic regeneration mismatch"):
        check(tmp_path)


def _write_fixture_package(
    root: Path,
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    authorization, rows, data_card, notice, manifest = built
    payloads = {
        AUTHORIZATION_OUTPUT_PATH: hard_negative_module._canonical_bytes(authorization),
        PAIR_PATH: _pair_bytes(rows),
        DATA_CARD_PATH: data_card,
        NOTICE_PATH: notice,
        MANIFEST_PATH: hard_negative_module._canonical_bytes(manifest),
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o644)


def test_nested_extra_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _write_fixture_package(tmp_path, built)
    nested = tmp_path / PACKAGE_DIRECTORY / "private"
    nested.mkdir()
    (nested / "raw.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(hard_negative_module, "build_package", lambda _root: built)

    with pytest.raises(ValueError, match="unsafe extra entry"):
        check(tmp_path)


def test_extra_symlink_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    built: tuple[dict[str, Any], list[dict[str, Any]], bytes, bytes, dict[str, Any]],
) -> None:
    _write_fixture_package(tmp_path, built)
    package_root = tmp_path / PACKAGE_DIRECTORY
    (package_root / "unsafe-link").symlink_to(package_root / "pairs.jsonl")
    monkeypatch.setattr(hard_negative_module, "build_package", lambda _root: built)

    with pytest.raises(ValueError, match="unsafe extra entry"):
        check(tmp_path)


def test_materialized_package_matches_strict_checker_and_hash_manifest() -> None:
    manifest = check(ROOT)
    pair_rows = _read_json_lines(ROOT / PAIR_PATH)

    assert manifest["files_sha256"]["pairs.jsonl"] == hashlib.sha256(
        (ROOT / PAIR_PATH).read_bytes()
    ).hexdigest()
    assert len(pair_rows) == manifest["aggregate_counts"]["pair_count"]
    assert _content_sha256(manifest["files_sha256"]) == manifest["package_sha256"]
    for relative in (
        AUTHORIZATION_OUTPUT_PATH,
        PAIR_PATH,
        DATA_CARD_PATH,
        NOTICE_PATH,
        MANIFEST_PATH,
    ):
        assert (ROOT / relative).stat().st_mode & 0o111 == 0


def test_git_allowlist_tracks_only_public_package_and_keeps_t2_private() -> None:
    for relative in (
        AUTHORIZATION_OUTPUT_PATH,
        PAIR_PATH,
        DATA_CARD_PATH,
        NOTICE_PATH,
        MANIFEST_PATH,
    ):
        assert subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", str(relative)],
            cwd=ROOT,
            check=False,
        ).returncode == 1
    assert subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", str(LOCAL_POOLS_PATH)],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "--quiet",
            str(PACKAGE_DIRECTORY / "private" / "raw.json"),
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "--quiet",
            str(PACKAGE_DIRECTORY.parent / "scratch" / "pairs.jsonl"),
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
