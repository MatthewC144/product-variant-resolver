from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / (
    "reports/release-field-review-batch-01/decision-events/decision-01-lamborghini.json"
)
SUBARU_EVENT = ROOT / (
    "reports/release-field-review-batch-01/decision-events/decision-02-subaru-brz.json"
)
NISSAN_EVENT = ROOT / (
    "reports/release-field-review-batch-01/decision-events/"
    "decision-03-nissan-skyline-2000gt-r-lbwk.json"
)


def _load_validator() -> ModuleType:
    path = ROOT / "scripts/validate_release_field_review_decision.py"
    spec = importlib.util.spec_from_file_location("validate_release_field_review_decision",path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator()


def _mutated_event(mutator: object) -> Path:
    data = json.loads(EVENT.read_text())
    assert callable(mutator)
    mutator(data)
    temporary = tempfile.NamedTemporaryFile(mode="w",suffix=".json",delete=False)
    with temporary:
        json.dump(data,temporary)
    return Path(temporary.name)


def test_lamborghini_event_validates_and_is_scoped() -> None:
    event = VALIDATOR.validate_event(EVENT)
    assert event["family_review_id"] == "fandom-family-174efb9bce3a441e"
    assert event["owner_authorization"]["response"] == "繼續下一步"
    assert "do not approve Subaru,Nissan,Audi" in event["owner_authorization"]["interpreted_scope"]
    assert event["canonical_promotion_authorized"] is False


def test_only_three_grounded_hyw93_fields_are_confirmed() -> None:
    event = VALIDATOR.validate_event(EVENT)
    confirmed = [decision for decision in event["field_decisions"] if decision["decision"] == "confirmed"]
    assert {(item["source_record_id"],item["field"],str(item["reviewed_value"])) for item in confirmed} == {
        ("fandom-row-cd91a09d2fb2f780","casting_name","Lamborghini Huracán Sterrato"),
        ("fandom-row-cd91a09d2fb2f780","toy_number","HYW93"),
        ("fandom-row-cd91a09d2fb2f780","release_year","2025"),
    }


def test_all_fifteen_physical_slots_remain_unknown() -> None:
    event = VALIDATOR.validate_event(EVENT)
    unknown = [decision for decision in event["field_decisions"] if decision["decision"] == "unknown"]
    assert len(unknown) == 15
    assert {item["field"] for item in unknown} == VALIDATOR.PHYSICAL_FIELDS
    assert all(item["reviewed_value"] is None for item in unknown)


def test_all_three_lamborghini_pairs_are_different_release() -> None:
    event = VALIDATOR.validate_event(EVENT)
    relationships = event["relationship_decisions"]
    assert len(relationships) == 3
    assert {item["decision"] for item in relationships} == {"different_release"}


def test_subaru_event_validates_with_exact_owner_scope() -> None:
    event = VALIDATOR.validate_event(SUBARU_EVENT)
    assert event["family_review_id"] == "fandom-family-b60363832032d566"
    assert event["owner_authorization"]["response"] == "是"
    assert "do not approve Nissan,Audi" in event["owner_authorization"]["interpreted_scope"]
    assert event["summary"]["required_field_decisions"] == 16
    assert event["summary"]["canonical_changes"] == 0


def test_subaru_confirms_only_literal_hyy12_note() -> None:
    event = VALIDATOR.validate_event(SUBARU_EVENT)
    confirmed = [decision for decision in event["field_decisions"] if decision["decision"] == "confirmed"]
    assert confirmed == [
        {
            "decision": "confirmed",
            "evidence_references": [
                "reports/release-field-review-batch-01/packet.json#fandom-row-3aa2e8967b2f55bf"
            ],
            "field": "variant_note",
            "reason": (
                "Owner confirms only that the frozen source text for HYY12 reads 2nd Color - "
                "Zamac;this does not confirm a physical color or row-level match to the older "
                "human variant."
            ),
            "reviewed_value": "2nd Color - Zamac",
            "source_record_id": "fandom-row-3aa2e8967b2f55bf",
        }
    ]


def test_subaru_physical_fields_unknown_and_rows_different() -> None:
    event = VALIDATOR.validate_event(SUBARU_EVENT)
    unknown = [decision for decision in event["field_decisions"] if decision["decision"] == "unknown"]
    assert len(unknown) == 15
    assert {decision["field"] for decision in unknown} == VALIDATOR.PHYSICAL_FIELDS
    assert {decision["decision"] for decision in event["relationship_decisions"]} == {
        "different_release"
    }


def test_nissan_event_validates_with_exact_owner_scope() -> None:
    event = VALIDATOR.validate_event(NISSAN_EVENT)
    assert event["family_review_id"] == "fandom-family-369b0be5855c0a1c"
    assert event["owner_authorization"]["response"] == "繼好下一步"
    assert "do not approve Audi" in event["owner_authorization"]["interpreted_scope"]
    assert event["summary"]["required_field_decisions"] == 20
    assert event["summary"]["canonical_changes"] == 0


def test_nissan_confirms_only_grounded_hyx54_candidate_fields() -> None:
    event = VALIDATOR.validate_event(NISSAN_EVENT)
    confirmed = [decision for decision in event["field_decisions"] if decision["decision"] == "confirmed"]
    assert {
        (decision["source_record_id"],decision["field"],str(decision["reviewed_value"]))
        for decision in confirmed
    } == {
        ("fandom-row-27fe2c9ab41942b8","casting_name","Nissan Skyline 2000GT-R LBWK"),
        ("fandom-row-27fe2c9ab41942b8","toy_number","HYX54"),
        ("fandom-row-27fe2c9ab41942b8","release_year","2025"),
        ("fandom-row-27fe2c9ab41942b8","series","HW J-Imports"),
        ("fandom-row-27fe2c9ab41942b8","tool_lineage_ref","Tooned"),
    }


def test_nissan_url_color_is_unknown_and_rows_are_different() -> None:
    event = VALIDATOR.validate_event(NISSAN_EVENT)
    unknown = [decision for decision in event["field_decisions"] if decision["decision"] == "unknown"]
    assert len(unknown) == 15
    assert {decision["field"] for decision in unknown} == VALIDATOR.PHYSICAL_FIELDS
    hyx54_color = next(
        decision
        for decision in unknown
        if decision["source_record_id"] == "fandom-row-27fe2c9ab41942b8"
        and decision["field"] == "color"
    )
    assert hyx54_color["reviewed_value"] is None
    assert "URL slug" in hyx54_color["reason"]
    assert {decision["decision"] for decision in event["relationship_decisions"]} == {
        "different_release"
    }


@pytest.mark.parametrize(
    ("mutator","message"),
    [
        (lambda event: event.update(packet_sha256="0" * 64),"packet SHA mismatch"),
        (lambda event: event.update(canonical_promotion_authorized=True),"canonical promotion"),
        (
            lambda event: event["field_decisions"][0].update(reviewed_value="Different casting"),
            "not grounded",
        ),
        (lambda event: event["field_decisions"].pop(),"required field decisions differ"),
        (lambda event: event["relationship_decisions"].pop(),"does not decide every"),
    ],
)
def test_tampered_events_fail(mutator: object,message: str) -> None:
    path = _mutated_event(mutator)
    try:
        with pytest.raises(ValueError,match=message):
            VALIDATOR.validate_event(path)
    finally:
        path.unlink()


def test_validator_has_no_network_database_or_write_path() -> None:
    source = (ROOT / "scripts/validate_release_field_review_decision.py").read_text()
    for forbidden in ("requests","httpx","urllib","sqlalchemy","psycopg","docker","write_text"):
        assert forbidden not in source
