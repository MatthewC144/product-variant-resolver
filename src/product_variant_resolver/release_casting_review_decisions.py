"""Record ordered, private owner decisions for local casting review batch 01."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .release_casting_review_batch import ALLOWED_DECISIONS, check_batch
from .release_staging import digest

SCHEMA_VERSION = "pvr-local-release-casting-owner-decision-ledger-v1"
EVENT_SCHEMA_VERSION = "pvr-local-release-casting-owner-decision-event-v1"
LEDGER_VERSION = "local-release-casting-owner-decisions-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-casting-owner-decisions-public-summary-v1"
EXCLUDED_EFFECTS = (
    "release_variant_approval",
    "physical_color_inference",
    "synthetic_product_selection",
    "canonical_uuid_creation",
    "postgresql_write",
    "evaluation_label_creation",
    "dual_rag_runtime_change",
)


def _normalized_response(value: str, expected_ordinal: int) -> str:
    response = value.strip()
    numbered_response = re.fullmatch(r"(\d+)\.\s*(.+)", response, flags=re.DOTALL)
    if numbered_response is not None:
        if int(numbered_response.group(1)) != expected_ordinal:
            raise ValueError("owner response question prefix differs from recorded question")
        response = numbered_response.group(2)
    return response.strip().strip("`").strip()


def _validate_timestamp(value: str) -> None:
    if not value.endswith("Z"):
        raise ValueError("decision timestamp must be UTC and end in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("decision timestamp must be valid ISO-8601") from error
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("decision timestamp must be UTC")


def _questions(packet: dict[str, Any]) -> list[dict[str, Any]]:
    questions = packet.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        raise ValueError("owner packet must contain exactly five questions")
    if not all(isinstance(item, dict) for item in questions):
        raise TypeError("owner packet questions must be objects")
    return questions


def _effect(decision: str) -> tuple[str, str]:
    if decision == "same_review_family":
        return (
            "review_family_relationship_confirmed",
            "same review-level casting family only; release variants, colors, synthetic products, "
            "and canonical UUIDs remain unapproved",
        )
    if decision == "keep_separate":
        return (
            "review_family_relationship_rejected",
            "keep the reviewed relationship separate without asserting a canonical identity",
        )
    return (
        "review_family_relationship_unresolved",
        "preserve the question without asserting or rejecting the review-level relationship",
    )


def build_event(
    packet: dict[str, Any],
    *,
    question_ordinal: int,
    decision: str,
    owner_response_verbatim: str,
    decided_at: str,
    event_sequence: int,
) -> dict[str, Any]:
    questions = _questions(packet)
    if question_ordinal < 1 or question_ordinal > len(questions):
        raise ValueError("question ordinal is outside the frozen packet")
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("decision is not allowed by the frozen packet")
    if _normalized_response(owner_response_verbatim, question_ordinal) != decision:
        raise ValueError("normalized owner response differs from the recorded decision")
    _validate_timestamp(decided_at)
    question = questions[question_ordinal - 1]
    if question.get("ordinal") != question_ordinal:
        raise ValueError("question ordinal differs from packet order")
    if decision not in question.get("allowed_decisions", []):
        raise ValueError("question does not allow the recorded decision")
    effect, interpretation = _effect(decision)
    body = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_sequence": event_sequence,
        "question_ordinal": question_ordinal,
        "review_cluster_id": question.get("review_cluster_id"),
        "packet_sha256": packet.get("packet_sha256"),
        "packet_batch_id": packet.get("batch_id"),
        "decided_by": "project_owner",
        "decided_at": decided_at,
        "owner_response_verbatim": owner_response_verbatim,
        "decision": decision,
        "authorized_effect": effect,
        "interpretation": interpretation,
        "excluded_effects": list(EXCLUDED_EFFECTS),
        "canonical_uuid": None,
        "color_decision": None,
    }
    return {**body, "event_sha256": digest(body)}


def _summary(events: list[dict[str, Any]], question_count: int) -> dict[str, Any]:
    counts = Counter(str(item["decision"]) for item in events)
    return {
        "total_questions": question_count,
        "recorded_owner_decisions": len(events),
        "pending_owner_decisions": question_count - len(events),
        "decision_counts": {decision: counts[decision] for decision in ALLOWED_DECISIONS},
        "review_family_relationships_confirmed": counts["same_review_family"],
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "network_requests": 0,
    }


def build_ledger(packet: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    questions = _questions(packet)
    status = "complete" if len(events) == len(questions) else "in_progress_awaiting_owner"
    body = {
        "schema_version": SCHEMA_VERSION,
        "ledger_version": LEDGER_VERSION,
        "status": status,
        "packet_sha256": packet.get("packet_sha256"),
        "packet_batch_id": packet.get("batch_id"),
        "events": events,
        "summary": _summary(events, len(questions)),
    }
    return {**body, "ledger_sha256": digest(body)}


def validate_ledger(packet: dict[str, Any], ledger: dict[str, Any]) -> None:
    questions = _questions(packet)
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("decision ledger schema differs from contract")
    if ledger.get("ledger_version") != LEDGER_VERSION:
        raise ValueError("decision ledger version differs from contract")
    if ledger.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("decision ledger is bound to another packet checksum")
    if ledger.get("packet_batch_id") != packet.get("batch_id"):
        raise ValueError("decision ledger is bound to another packet batch")
    events = ledger.get("events")
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise TypeError("decision ledger events must be a list of objects")
    if len(events) > len(questions):
        raise ValueError("decision ledger has more events than questions")
    for index, event in enumerate(events, start=1):
        if event.get("event_sequence") != index or event.get("question_ordinal") != index:
            raise ValueError("decision events must be contiguous and ordered by question")
        expected = build_event(
            packet,
            question_ordinal=index,
            decision=str(event.get("decision")),
            owner_response_verbatim=str(event.get("owner_response_verbatim")),
            decided_at=str(event.get("decided_at")),
            event_sequence=index,
        )
        if event != expected:
            raise ValueError(f"decision event {index} differs from its deterministic contract")
    expected_ledger = build_ledger(packet, events)
    if ledger != expected_ledger:
        raise ValueError("decision ledger summary, status, or checksum differs from events")


def append_event(
    packet: dict[str, Any],
    ledger: dict[str, Any] | None,
    *,
    question_ordinal: int,
    decision: str,
    owner_response_verbatim: str,
    decided_at: str,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    if ledger is not None:
        validate_ledger(packet, ledger)
        events = list(ledger["events"])
    expected_ordinal = len(events) + 1
    if question_ordinal != expected_ordinal:
        raise ValueError(f"next unanswered question is {expected_ordinal}")
    event = build_event(
        packet,
        question_ordinal=question_ordinal,
        decision=decision,
        owner_response_verbatim=owner_response_verbatim,
        decided_at=decided_at,
        event_sequence=expected_ordinal,
    )
    result = build_ledger(packet, [*events, event])
    validate_ledger(packet, result)
    return result


def build_public_manifest(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "ledger_version": LEDGER_VERSION,
        "status": ledger["status"],
        "public_scope": "aggregate_progress_and_hashes_only_no_questions_labels_or_verbatim_answers",
        "packet_sha256": ledger["packet_sha256"],
        "packet_batch_id": ledger["packet_batch_id"],
        "ledger_sha256": ledger["ledger_sha256"],
        "summary": ledger["summary"],
    }


def render_public_report(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    return "\n".join(
        [
            "# Local release casting owner decisions — public progress",
            "",
            "Owner decisions are stored in a private checksum-bound ledger.",
            "This report contains aggregate progress only.",
            "",
            f"- Recorded owner decisions: {summary['recorded_owner_decisions']} / {summary['total_questions']}",
            f"- Pending owner decisions: {summary['pending_owner_decisions']}",
            f"- `same_review_family`: {summary['decision_counts']['same_review_family']}",
            f"- `keep_separate`: {summary['decision_counts']['keep_separate']}",
            f"- `unknown`: {summary['decision_counts']['unknown']}",
            f"- Review-family relationships confirmed: {summary['review_family_relationships_confirmed']}",
            "- Canonical promotions: 0",
            "- Reviewed colors: 0",
            "- PostgreSQL writes: 0",
            "- Network requests: 0",
            "",
            "The next gate is the next unanswered frozen question.",
            "No recorded relationship is a release-variant or canonical-product approval.",
            "",
        ]
    )


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return payload


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _replace(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _packet(root: Path) -> dict[str, Any]:
    private_batch = root / "data/external/hot-wheels-wiki/local-release-casting-review-batch-01"
    public_batch = root / "reports/local-release-casting-review-batch-01"
    check_batch(root, private_batch, public_batch)
    return _load_object(private_batch / "packet.json")


def record_decision(
    root: Path,
    *,
    question_ordinal: int,
    decision: str,
    owner_response_verbatim: str,
    decided_at: str,
) -> dict[str, Any]:
    packet = _packet(root)
    private_directory = (
        root / "data/external/hot-wheels-wiki/local-release-casting-review-decisions-v1"
    )
    public_directory = root / "reports/local-release-casting-review-decisions-v1"
    ledger_path = private_directory / "ledger.json"
    existing = _load_object(ledger_path) if ledger_path.is_file() else None
    ledger = append_event(
        packet,
        existing,
        question_ordinal=question_ordinal,
        decision=decision,
        owner_response_verbatim=owner_response_verbatim,
        decided_at=decided_at,
    )
    manifest = build_public_manifest(ledger)
    private_directory.mkdir(exist_ok=True)
    public_directory.mkdir(exist_ok=True)
    _replace(ledger_path, _stable_json(ledger))
    _replace(public_directory / "manifest.json", _stable_json(manifest))
    _replace(public_directory / "report.md", render_public_report(manifest))
    check_decisions(root)
    return ledger


def check_decisions(root: Path) -> dict[str, Any]:
    packet = _packet(root)
    private_directory = (
        root / "data/external/hot-wheels-wiki/local-release-casting-review-decisions-v1"
    )
    public_directory = root / "reports/local-release-casting-review-decisions-v1"
    expected_private = {"ledger.json"}
    expected_public = {"manifest.json", "report.md"}
    if (
        not private_directory.is_dir()
        or {path.name for path in private_directory.iterdir()} != expected_private
    ):
        raise ValueError("private decision directory differs from contract")
    if (
        not public_directory.is_dir()
        or {path.name for path in public_directory.iterdir()} != expected_public
    ):
        raise ValueError("public decision directory differs from contract")
    ledger = _load_object(private_directory / "ledger.json")
    validate_ledger(packet, ledger)
    manifest = build_public_manifest(ledger)
    if (public_directory / "manifest.json").read_text(encoding="utf-8") != _stable_json(manifest):
        raise ValueError("public decision manifest differs from private ledger")
    if (public_directory / "report.md").read_text(encoding="utf-8") != render_public_report(
        manifest
    ):
        raise ValueError("public decision report differs from private ledger")
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser(description="Record or verify local casting owner decisions")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--question", type=int)
    parser.add_argument("--decision", choices=ALLOWED_DECISIONS)
    parser.add_argument("--owner-response")
    parser.add_argument("--decided-at")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.check:
        ledger = check_decisions(root)
        status = "valid"
    else:
        if None in (
            arguments.question,
            arguments.decision,
            arguments.owner_response,
            arguments.decided_at,
        ):
            parser.error(
                "recording requires --question, --decision, --owner-response and --decided-at"
            )
        ledger = record_decision(
            root,
            question_ordinal=arguments.question,
            decision=arguments.decision,
            owner_response_verbatim=arguments.owner_response,
            decided_at=arguments.decided_at,
        )
        status = "recorded"
    print(
        json.dumps(
            {
                "status": status,
                "ledger_sha256": ledger["ledger_sha256"],
                "summary": ledger["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
