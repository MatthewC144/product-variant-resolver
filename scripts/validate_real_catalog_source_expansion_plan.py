#!/usr/bin/env python3
"""Validate the planning-only VAR-PLAN2 source gate without network or database access."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "reports/real-catalog-source-expansion-v1/plan.json"

EXPECTED_COUNTERS = {
    "requests_attempted",
    "requests_succeeded",
    "cache_hits",
    "pages",
    "revisions",
    "raw_observations",
    "deduplicated_source_releases",
    "castings",
    "held_releases",
    "conflicted_releases",
    "unresolved_releases",
    "owner_reviewed_variants",
    "canonical_products",
    "errors",
}
EXPECTED_STOPS = {
    "missing_or_expired_written_permission",
    "permission_scope_mismatch",
    "terms_or_robots_drift",
    "http_401",
    "http_403",
    "http_429_or_rate_limit",
    "captcha_or_access_challenge",
    "unexpected_redirect_or_schema",
    "revision_or_checksum_mismatch",
    "community_license_unverified",
    "owner_budget_not_approved",
}
EXPECTED_RESEARCH = {
    "fandom-terms-2025-12-19",
    "fandom-general-licensing",
    "mediawiki-api-etiquette-8373208",
}


def _reject_duplicate_keys(pairs: list[tuple[str,Any]]) -> dict[str,Any]:
    result: dict[str,Any] = {}
    for key,value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str,Any]:
    value = json.loads(path.read_text(),object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value,dict):
        raise ValueError("plan must be an object")
    return value


def validate_plan(path: Path = DEFAULT_PLAN) -> dict[str,Any]:
    plan = _load(path)
    if plan.get("schema_version") != "pvr-real-catalog-source-expansion-plan-v1":
        raise ValueError("unexpected plan schema")
    if plan.get("status") != "blocked":
        raise ValueError("plan must remain blocked")

    authority = plan.get("authority")
    expected_authority = {
        "planning_only": True,
        "collection_enabled": False,
        "executed_remote_requests": 0,
        "database_writes_authorized": False,
        "images_allowed": False,
        "ocr_allowed": False,
        "canonical_changes_authorized": 0,
    }
    if authority != expected_authority:
        raise ValueError("planning authority boundary changed")

    gate = plan.get("current_gate")
    if not isinstance(gate,dict) or gate.get("status") != (
        "blocked_pending_fandom_written_permission_and_owner_canary_approval"
    ):
        raise ValueError("current source gate is not blocked")
    if not all(isinstance(gate.get(field),str) and gate[field] for field in ("blocking_reason","next_action")):
        raise ValueError("source gate explanation missing")

    sources = plan.get("source_candidates")
    if not isinstance(sources,list) or len(sources) != 1 or not isinstance(sources[0],dict):
        raise ValueError("expected one explicit source candidate")
    source = sources[0]
    if source.get("source_id") != "hot-wheels-fandom-text":
        raise ValueError("unexpected source candidate")
    if source.get("automated_access_status") != "blocked_pending_express_written_permission":
        raise ValueError("Fandom automated access must remain blocked")
    if source.get("permission_evidence") is not None or source.get("approved_endpoints") != []:
        raise ValueError("permission/endpoints cannot be approved in this plan")
    if source.get("community_specific_license_status") != "unverified":
        raise ValueError("Hot Wheels Wiki license must remain unverified")
    if source.get("media_allowed") is not False:
        raise ValueError("media must remain excluded")

    research = plan.get("research_evidence")
    if not isinstance(research,list) or not all(isinstance(item,dict) for item in research):
        raise ValueError("research evidence missing")
    if {item.get("evidence_id") for item in research} != EXPECTED_RESEARCH:
        raise ValueError("research evidence set changed")
    for item in research:
        if not all(isinstance(item.get(field),str) and item[field] for field in (
            "publisher","url","checked_at_utc","observed_rule","retrieval_limitation","scope",
            "authority_effect",
        )):
            raise ValueError(f"research evidence incomplete: {item.get('evidence_id')}")
        if not item["url"].startswith("https://"):
            raise ValueError("research URL must use HTTPS")

    canary = plan.get("conditional_canary")
    if not isinstance(canary,dict) or canary.get("status") != "proposal_not_approved":
        raise ValueError("canary must remain unapproved")
    budget = canary.get("request_budget")
    if budget != {"executed_requests":0,"maximum_if_later_approved":3}:
        raise ValueError("canary request budget changed")
    requirements = canary.get("requires")
    if not isinstance(requirements,list) or {
        "express_written_fandom_permission_artifact",
        "separate_project_owner_canary_approval",
    } - set(requirements):
        raise ValueError("canary authority gates missing")
    transport = canary.get("transport_floor_if_later_approved")
    if not isinstance(transport,dict) or (
        transport.get("concurrency") != 1
        or transport.get("minimum_delay_seconds",0) < 5
        or transport.get("maxlag_seconds") != 1
        or transport.get("cache_required") is not True
        or transport.get("descriptive_contact_user_agent_required") is not True
    ):
        raise ValueError("conditional transport floor is unsafe")

    milestones = plan.get("expansion_milestones")
    if not isinstance(milestones,list) or [
        milestone.get("target_unique_real_source_rows") for milestone in milestones
    ] != [100,500,1500,3000]:
        raise ValueError("expansion milestones changed")
    if any(milestone.get("current_request_budget") != 0 for milestone in milestones):
        raise ValueError("current milestone request budgets must be zero")
    if milestones[0].get("status") != "existing_offline_baseline_only" or any(
        milestone.get("status") != "blocked_pending_prior_gate" for milestone in milestones[1:]
    ):
        raise ValueError("milestone gate status changed")

    if set(plan.get("required_counters",[])) != EXPECTED_COUNTERS:
        raise ValueError("required counters changed")
    if set(plan.get("stop_conditions",[])) != EXPECTED_STOPS:
        raise ValueError("stop conditions changed")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",type=Path,default=DEFAULT_PLAN)
    args = parser.parse_args()
    try:
        plan = validate_plan(args.check)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as error:
        print(f"source expansion plan rejected: {error}",file=sys.stderr)
        return 1
    print(
        "PASS source expansion plan: "
        f"status={plan['status']};sources={len(plan['source_candidates'])};"
        f"milestones={len(plan['expansion_milestones'])};remote_requests=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
