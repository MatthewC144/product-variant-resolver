from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "reports/real-catalog-source-expansion-v1/plan.json"


def _load_validator() -> ModuleType:
    path = ROOT / "scripts/validate_real_catalog_source_expansion_plan.py"
    spec = importlib.util.spec_from_file_location("validate_real_catalog_source_expansion_plan",path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator()


def _mutated_plan(mutator: object) -> Path:
    data = json.loads(PLAN.read_text())
    assert callable(mutator)
    mutator(data)
    temporary = tempfile.NamedTemporaryFile(mode="w",suffix=".json",delete=False)
    with temporary:
        json.dump(data,temporary)
    return Path(temporary.name)


def test_plan_validates_as_blocked_planning_only() -> None:
    plan = VALIDATOR.validate_plan(PLAN)
    assert plan["status"] == "blocked"
    assert plan["authority"]["collection_enabled"] is False
    assert plan["authority"]["executed_remote_requests"] == 0


def test_fandom_license_and_access_permission_are_separate() -> None:
    plan = VALIDATOR.validate_plan(PLAN)
    source = plan["source_candidates"][0]
    assert "CC BY-SA3.0" in source["general_text_license_context"]
    assert source["community_specific_license_status"] == "unverified"
    assert source["automated_access_status"] == "blocked_pending_express_written_permission"
    assert source["permission_evidence"] is None
    assert source["approved_endpoints"] == []


def test_canary_and_all_milestones_have_zero_current_requests() -> None:
    plan = VALIDATOR.validate_plan(PLAN)
    assert plan["conditional_canary"]["request_budget"]["executed_requests"] == 0
    assert plan["conditional_canary"]["request_budget"]["maximum_if_later_approved"] == 3
    assert all(item["current_request_budget"] == 0 for item in plan["expansion_milestones"])


def test_scale_targets_and_separate_counters_are_explicit() -> None:
    plan = VALIDATOR.validate_plan(PLAN)
    assert [item["target_unique_real_source_rows"] for item in plan["expansion_milestones"]] == [
        100,
        500,
        1500,
        3000,
    ]
    assert {"raw_observations","deduplicated_source_releases","owner_reviewed_variants","canonical_products"} <= set(
        plan["required_counters"]
    )


@pytest.mark.parametrize(
    ("mutator","message"),
    [
        (lambda plan: plan["authority"].update(collection_enabled=True),"authority boundary"),
        (lambda plan: plan["source_candidates"][0].update(permission_evidence="invented"),"permission"),
        (lambda plan: plan["source_candidates"][0]["approved_endpoints"].append("/api.php"),"permission"),
        (lambda plan: plan["conditional_canary"]["request_budget"].update(executed_requests=1),"budget"),
        (lambda plan: plan["expansion_milestones"][1].update(current_request_budget=1),"budgets"),
        (lambda plan: plan["stop_conditions"].remove("captcha_or_access_challenge"),"stop conditions"),
    ],
)
def test_authority_tampering_fails_closed(mutator: object,message: str) -> None:
    path = _mutated_plan(mutator)
    try:
        with pytest.raises(ValueError,match=message):
            VALIDATOR.validate_plan(path)
    finally:
        path.unlink()


def test_validator_has_no_network_database_or_write_path() -> None:
    source = (ROOT / "scripts/validate_real_catalog_source_expansion_plan.py").read_text()
    for forbidden in (
        "import requests",
        "from requests",
        "import httpx",
        "import urllib",
        "import sqlalchemy",
        "import psycopg",
        "import socket",
        "write_text",
        "open(\"w\"",
    ):
        assert forbidden not in source
