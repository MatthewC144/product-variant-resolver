from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from product_variant_resolver.human_knowledge import (
    CharacterIdentityIndex,
    HumanKnowledgeRetriever,
    load_human_knowledge_catalog,
)
from product_variant_resolver.human_knowledge_selection import ROOT, synthetic_catalog

SCRIPT = ROOT / "scripts/build_human_knowledge_identity_protocol.py"
DIRECTORY = ROOT / "data/evaluation/human-knowledge-identity-development-v1"


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("identity_protocol_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def catalog():
    return load_human_knowledge_catalog(ROOT / "data/human_backed_catalog.json",
                                       ROOT / "data/review_family_knowledge.json",
                                       ROOT / "data/review_family_knowledge_manifest.json")


def read(name: str) -> dict:
    return json.loads((DIRECTORY / name).read_text(encoding="utf-8"))


def test_all_frozen_artifacts_are_byte_reproducible_and_snapshot_portable(builder) -> None:
    # --check works from delivered snapshots without access to the old Git commit.
    with patch.object(subprocess, "run", side_effect=AssertionError("check must not require Git")):
        builder.check(DIRECTORY)
    generated = builder.build(builder.approved_specs(DIRECTORY))
    for name, text in generated.items():
        assert (DIRECTORY / name).read_text(encoding="utf-8") == text


def test_protocol_build_never_executes_retrieval_or_reads_final_v1(builder) -> None:
    original_bytes, original_text = Path.read_bytes, Path.read_text

    def bytes_guard(path):
        assert "family-retrieval-v1" not in str(path)
        return original_bytes(path)

    def text_guard(path, *args, **kwargs):
        assert "family-retrieval-v1" not in str(path)
        return original_text(path, *args, **kwargs)

    with patch.object(Path, "read_bytes", bytes_guard), patch.object(Path, "read_text", text_guard), patch.object(HumanKnowledgeRetriever, "retrieve", side_effect=AssertionError("retrieval prohibited")), patch.object(CharacterIdentityIndex, "rank", side_effect=AssertionError("ranking prohibited")):
        builder.check(DIRECTORY)


def test_owner_approval_and_viewed_dev_disclosure(builder) -> None:
    approval, protocol = read("owner-approval.json"), read("protocol.json")
    assert approval["authority"] == "project_owner"
    assert approval["approval_instruction"] == "執行下一步"
    assert approval["approved_commit"] == builder.APPROVED_COMMIT
    assert approval["approved_spec_sha256"] == builder.SPEC_HASHES
    assert protocol["owner_approval"] == approval
    assert protocol["v4_retrieval_executed"] is False
    assert protocol["v4_configuration_output_viewed"] is False
    assert "viewed_identity_derived_199_development_cases_reused_not_blind" in protocol["limitations"]
    assert "final_accuracy_claim" in protocol["excluded_from"]


def test_exact_real_core_counts_and_allowed_same_casting_collisions(builder) -> None:
    audit = read("identity-core-audit.json")["real"]
    assert audit["document_count"] == 142
    assert audit["knowledge_type_counts"] == {"provisional_variant": 100, "review_family": 42}
    assert audit["form_count"] == 284
    assert audit["max_forms_per_document"] == 2
    assert audit["collision_group_count"] == 2
    assert audit["cross_casting_collision_group_count"] == 0
    assert {item["core"] for item in audit["collisions"]} == {"83 chevy silverado", "toyota supra"}
    assert all(len(item["original_castings"]) == 1 for item in audit["collisions"])
    assert len({row["knowledge_id"] for row in audit["documents"]}) == 142
    assert len({form["form_id"] for row in audit["documents"] for form in row["forms"]}) == 284
    assert all(form["text"] and form["gram_count"] > 0
               for row in audit["documents"] for form in row["forms"])


def test_shared_whole_token_noise_policy_unicode_and_numbers(builder) -> None:
    assert builder.core("ｔＯＹＯＴＡ Supra blue") == "toyota supra"
    assert builder.core("Boxster boxed red") == "boxster"
    assert builder.core("Ford F-150 red") == "ford f 150"
    assert builder.core("Scale vehicle model 0001") == "0001"
    development = json.loads((ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json").read_text())
    generic = [row for row in development["cases"] if row["challenge_style"] == "generic_no_identity"]
    assert len(generic) == 10
    assert all(builder.core(row["query_text"]) == "" for row in generic)


def test_reject_empty_short_duplicate_and_excessive_identity_forms(builder, catalog) -> None:
    variant = next(item for item in catalog.documents if item.knowledge_type == "provisional_variant")
    family = next(item for item in catalog.documents if item.knowledge_type == "review_family")
    with pytest.raises(ValueError, match="empty identity"):
        builder.identity_audit((replace(variant, casting="blue model"),))
    with pytest.raises(ValueError, match="too short"):
        builder.identity_audit((replace(variant, casting="A"),))
    with pytest.raises(ValueError, match="empty identity"):
        builder.identity_audit((replace(family, aliases=("model",)),))
    with pytest.raises(ValueError, match="duplicate knowledge UUID"):
        builder.identity_audit((variant, variant))
    with pytest.raises(ValueError, match="form limit"):
        builder.identity_audit((replace(family, aliases=tuple(f"distinct identity {index}" for index in range(17))),))
    assert builder.identity_audit((replace(variant, human_label_names=("ignored blue listing",),
                                           pricing_keywords=("ignored private keyword",),
                                           initial_names=("ignored recognition text",)),)) == builder.identity_audit((variant,))


def test_exact_scale_workload_targets_and_group_shapes() -> None:
    protocol = read("protocol.json")
    rows = protocol["scale_workload"]
    assert Counter(row["group"] for row in rows) == {
        "original_dev_20": 20, "exact_identity": 60, "single_edit": 20, "contextual_identity": 20}
    assert len({row["case_id"] for row in rows}) == 120
    documents = synthetic_catalog().documents
    for index, row in enumerate(rows[20:]):
        assert row["target_knowledge_id"] == documents[index].knowledge_id
        assert row["target_knowledge_uuid"] == str(documents[index].knowledge_uuid)
        assert row["correctness_eligible"] is True
        expected = (documents[index].casting if index < 60 else
                    documents[index].casting.replace("Scale", "Scxle", 1) if index < 80 else
                    f"listing {documents[index].casting} local pickup")
        assert row["query_text"] == expected
    assert all(row["target_knowledge_id"] is None and not row["correctness_eligible"] for row in rows[:20])
    assert "synthetic_casting_cores_are_numeric_only" in protocol["limitations"]
    assert "scale_single_edit_changes_noise_token_not_numeric_target_identity" in protocol["limitations"]


def test_grid_limits_cost_and_correctness_gates_are_fixed(builder) -> None:
    protocol = read("protocol.json")
    contract = protocol["selection_contract"]
    assert contract["character_score_floors"] == [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55]
    assert contract["character_rrf_weights"] == [0.5, 1.0, 1.5]
    assert contract["configuration_count"] == 21
    assert contract["candidate_limit"] == 5
    assert protocol["limits"] == builder.LIMITS
    cost = protocol["cost_protocol"]
    assert (cost["real_sample_count"], cost["scale_sample_count"]) == (199, 120)
    assert (cost["real_p95_max_ms"], cost["scale_p95_max_ms"]) == (25, 150)
    assert (cost["scale_exact_hits_required"], cost["scale_context_hits_required"], cost["scale_single_edit_hits_required"]) == (60, 20, 17)
    assert cost["positive_abstentions_count_as_misses"]
    assert protocol["audit_summary"]["max_real_query_forms"] == 90
    assert protocol["audit_summary"]["max_scale_query_forms"] == 60


def test_query_limits_fail_before_protocol_publication(builder) -> None:
    with pytest.raises(ValueError, match="query limits"):
        builder.query_form_count("z" * 513, [1])
    with pytest.raises(ValueError, match="query limits"):
        builder.query_form_count(" ".join(f"a{index}" for index in range(65)), [1])
    with pytest.raises(ValueError, match="window limit"):
        builder.query_form_count(" ".join(f"a{index}" for index in range(30)), list(range(1, 9)))
    assert builder.query_form_count("blue boxed car", [1, 2]) == 0


def test_manifest_binds_every_generated_file_and_protected_input(builder) -> None:
    manifest = read("protocol-manifest.json")
    assert set(manifest["file_sha256"]) == {
        "protocol.json", "identity-core-audit.json", "owner-approval.json",
        "approved-specs/requirements.md", "approved-specs/design.md", "approved-specs/tasks.md"}
    for name, checksum in manifest["file_sha256"].items():
        assert hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() == checksum
    for name, checksum in manifest["input_sha256"].items():
        assert "family-retrieval-v1" not in name
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == checksum
    assert manifest["input_sha256"]["scripts/build_human_knowledge_identity_protocol.py"] == builder.sha(SCRIPT)


def test_invalid_input_and_changed_frozen_outputs_are_preserved(builder, tmp_path: Path) -> None:
    target = tmp_path / "protocol"
    shutil.copytree(DIRECTORY, target)
    before = {str(path.relative_to(target)): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    specs = builder.approved_specs(DIRECTORY)
    invalid = dict(specs)
    invalid["design.md"] += "altered policy"
    with pytest.raises(ValueError, match="snapshots"):
        builder.freeze(target, invalid)
    assert all((target / name).read_bytes() == value for name, value in before.items())
    (target / "protocol.json").write_text("changed frozen sentinel", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        builder.freeze(target, specs)
    assert (target / "protocol.json").read_text() == "changed frozen sentinel"
    assert all((target / name).read_bytes() == value for name, value in before.items() if name != "protocol.json")
    with pytest.raises(ValueError, match="stale or changed"):
        builder.check(target)


def test_freeze_is_idempotent_without_replacing_existing_files(builder, tmp_path: Path) -> None:
    target = tmp_path / "protocol"
    shutil.copytree(DIRECTORY, target)
    times = {path: path.stat().st_mtime_ns for path in target.rglob("*") if path.is_file()}
    builder.freeze(target, builder.approved_specs(DIRECTORY))
    assert all(path.stat().st_mtime_ns == timestamp for path, timestamp in times.items())
