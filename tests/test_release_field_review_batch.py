from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_preparer() -> ModuleType:
    path = ROOT / "scripts/prepare_release_field_review_batch.py"
    spec = importlib.util.spec_from_file_location("prepare_release_field_review_batch", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARER = _load_preparer()


def test_packet_has_exact_frozen_batch_and_zero_authority() -> None:
    packet = PREPARER.build_packet()
    assert packet["counts"] == {
        "families": 4,
        "source_rows": 11,
        "relationship_pairs": 10,
        "row_specific_candidate_claims": 3,
        "owner_field_decisions": 0,
        "owner_relationship_decisions": 0,
        "canonical_uuids": 0,
    }
    assert packet["status"] == "awaiting_owner_review_no_decisions"
    assert packet["authority"]["all_rows_held"] is True
    assert packet["authority"]["prior_family_decisions_are_release_decisions"] is False


def test_rows_are_unique_held_and_keep_physical_fields_unknown() -> None:
    packet = PREPARER.build_packet()
    rows = [row for family in packet["families"] for row in family["rows"]]
    assert len({row["source_record_id"] for row in rows}) == 11
    assert len({row["observation_id"] for row in rows}) == 11
    for row in rows:
        assert row["review_state"] == {
            "status": "held_pending_owner_review",
            "canonical_uuid": None,
            "variant_equivalence_id": None,
            "field_decision_count": 0,
        }
        for field in ("color", "wheel_type", "tampo_description", "edition", "packaging_variant"):
            assert row["raw_fields"][field] is None


def test_family_evidence_is_casting_scoped_only() -> None:
    packet = PREPARER.build_packet()
    assert {family["prior_family_decision"] for family in packet["families"]} == {
        "create_new_casting",
        "merge_existing_family",
        "hold",
    }
    for family in packet["families"]:
        evidence = family["family_evidence"]
        assert evidence["approved_scope"] == "casting_family_only"
        assert evidence["release_effect"] == "none_all_source_rows_remain_held"


def test_only_three_exact_row_specific_claims_are_surfaced() -> None:
    packet = PREPARER.build_packet()
    claims_by_row = {
        row["source_record_id"]: row["candidate_secondary_claims"]
        for family in packet["families"]
        for row in family["rows"]
        if row["candidate_secondary_claims"]
    }
    assert set(claims_by_row) == {
        "fandom-row-65987b3eab315de1",
        "fandom-row-cd91a09d2fb2f780",
        "fandom-row-27fe2c9ab41942b8",
    }
    assert claims_by_row["fandom-row-65987b3eab315de1"][0]["candidate_fields"]["edition"] == (
        "Super Treasure Hunt"
    )
    nissan = claims_by_row["fandom-row-27fe2c9ab41942b8"][0]
    assert nissan["candidate_fields"]["tool_lineage_ref"] == "Tooned"
    assert "color" not in nissan["candidate_fields"]
    assert nissan["explicit_non_claims"]


def test_relationship_pairs_are_unique_within_family() -> None:
    packet = PREPARER.build_packet()
    pairs = []
    for family in packet["families"]:
        family_ids = {row["source_record_id"] for row in family["rows"]}
        for pair in family["relationship_pairs"]:
            assert pair["left_source_record_id"] in family_ids
            assert pair["right_source_record_id"] in family_ids
            assert pair["decision"] is None
            pairs.append(
                tuple(sorted((pair["left_source_record_id"], pair["right_source_record_id"])))
            )
    assert len(pairs) == len(set(pairs)) == 10


def test_decision_template_is_completely_pending() -> None:
    packet = PREPARER.build_packet()
    packet_bytes = PREPARER._json_bytes(packet)
    template = PREPARER.build_decision_template(packet, hashlib.sha256(packet_bytes).hexdigest())
    assert template["reviewer"] is None and template["reviewed_at"] is None
    assert template["canonical_promotion_authorized"] is False
    assert len(template["row_field_decisions"]) == 11
    assert len(template["relationship_decisions"]) == 10
    for row in template["row_field_decisions"]:
        assert len(row["fields"]) == 13
        assert all(field["decision"] is None for field in row["fields"].values())
    assert all(item["decision"] is None for item in template["relationship_decisions"])


def test_manifest_hashes_every_artifact() -> None:
    files = PREPARER.payloads()
    manifest = json.loads(files["manifest.json"])
    for name in ("packet.json", "owner-review.md", "decisions.template.json"):
        assert manifest["artifact_sha256"][name] == hashlib.sha256(files[name]).hexdigest()
    assert manifest["constraints"]["owner_decisions"] == 0
    assert manifest["constraints"]["network_requests"] == 0


def test_committed_packet_recomputes_exactly() -> None:
    PREPARER.check(PREPARER.DEFAULT_OUTPUT)


def test_publication_is_exclusive_and_drift_fails() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "batch"
        PREPARER.publish(output)
        with pytest.raises(ValueError,match="already exists"):
            PREPARER.publish(output)
        (output / "owner-review.md").write_text("changed")
        with pytest.raises(ValueError,match="owner-review.md drift"):
            PREPARER.check(output)


def test_changed_plan_batch_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        inputs = (PREPARER.PLAN_PATH,PREPARER.NORMALIZED_PATH,*PREPARER.EVIDENCE_PATHS)
        for relative in inputs:
            target = temporary_root / relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT / relative,target)
        plan_path = temporary_root / PREPARER.PLAN_PATH
        plan = json.loads(plan_path.read_text())
        plan["first_review_batch"]["family_count"] = 3
        plan_path.write_text(json.dumps(plan))
        with pytest.raises(ValueError,match="four-family/11-row"):
            PREPARER.build_packet(temporary_root)


def test_preparer_imports_no_network_or_database_client() -> None:
    source = (ROOT / "scripts/prepare_release_field_review_batch.py").read_text()
    for forbidden in ("requests","httpx","urllib","sqlalchemy","psycopg","docker"):
        assert f"import {forbidden}" not in source
